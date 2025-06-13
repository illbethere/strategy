# coding:GBK
import sys
import time
from datetime import datetime, timedelta

import QuantLib as ql
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from QuantLib import Bisection
from xtquant import xtdata

from xtquant import xtdatacenter as xtdc
xtdc.set_token('4065054877ce5724155dbc5bcba200381ce5eb35')
xtdc.init()


class G():
    pass


g = G()
g.option_code = '10009171.SHO'
g.iv_df = pd.DataFrame()


def plt_output(hv_data, iv_data, title, max_date_ticks=20):
    """������ʷ������(HV)������������(IV)������ͼ��"""
    # ����֧�����ĵ�����
    plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "sans-serif"]

    plt.figure(figsize=(14, 7))

    # ������ʷ������(HV)
    if isinstance(hv_data, pd.DataFrame) and 'HV' in hv_data.columns:
        plt.plot(hv_data.index, hv_data['HV'], label='��ʷ������(HV)', linewidth=2, color='blue')
    else:
        print("����: HV���ݸ�ʽ����ȷ��ȱ��'HV'��")

    # ��������������(IV)
    if isinstance(iv_data, pd.DataFrame) and 'IV' in iv_data.columns:
        plt.plot(iv_data.index, iv_data['IV'], label='����������(IV)', linewidth=2, color='red')
    else:
        print("����: IV���ݸ�ʽ����ȷ��ȱ��'IV'��")

    plt.title(f'{title} �����ʷ���')
    plt.xlabel('����')
    plt.ylabel('������')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best')  # ��ʾͼ��
    # �Ż�������ʾ
    ax = plt.gca()
    # date_format = mdates.DateFormatter('%Y-%m-%d')
    # ax.xaxis.set_major_formatter(date_format)

    if max_date_ticks > 0:
        ax.xaxis.set_major_locator(plt.MaxNLocator(max_date_ticks))
    # �Զ���ת���ڱ�ǩ�����ص�
    plt.xticks(rotation=45)
    plt.tight_layout()  # ȷ����ǩ�ͱ��ⲻ���ü�
    plt.show()


def get_hv(opt_code, rolling_window=20):
    def calculate_hv(df, window=20):
        """
        ���ڱ���ʲ����̼ۼ�����ʷ������
        :param df: ��ĵ�dataframe�������'close'��'preClose'��
        :param window: ��������(������)
        :return: ����HV�е�DataFrame
        """

        df = df.copy()
        log_return = np.log(df['close'] / df['preClose'])
        squared_returns = log_return ** 2
        realized_variance = squared_returns.rolling(window).sum() * (252 / window)
        realized_vol = np.sqrt(realized_variance)

        result_df = df.copy()
        result_df['HV'] = realized_vol
        return result_df.dropna(subset=['HV'])

    xtdata.download_history_contracts()
    option_info = xtdata.get_option_detail_data(opt_code)
    opt_detail = xtdata.get_option_detail_data(opt_code)
    # open_date = datetime.striptime(option_info['OpenDate'], '%Y%m%d').date()

    xtdata.download_history_data(opt_code, period="1d")
    opt_data = xtdata.get_market_data_ex(field_list=[], stock_list=[opt_code], period='1d',
                                         count=-1, dividend_type='none', fill_data=True)[opt_code]

    underlying_code = opt_detail['OptUndlCodeFull']
    start_date = option_info['OpenDate']
    extended_start_date = (datetime.strptime(start_date, '%Y%m%d') - timedelta(days=2 * rolling_window)).strftime(
        '%Y%m%d')
    xtdata.subscribe_quote(underlying_code, period='1d', start_time=extended_start_date,
                           end_time=option_info['ExpireDate'], count=-1, callback=None)
    xtdata.download_history_data(underlying_code, period='1d', start_time=extended_start_date,
                                 end_time=option_info['ExpireDate'])
    underlying_data = xtdata.get_market_data_ex(field_list=[], stock_list=[underlying_code], period='1d',
                                                start_time=extended_start_date, end_time=option_info['ExpireDate'],
                                                count=-1, dividend_type='none', fill_data=True)[underlying_code]

    # ��ȡ����
    date_list = opt_data.index.to_list()
    date_list = [str(d) for d in date_list]

    underlying_data_hv = pd.DataFrame(calculate_hv(underlying_data), columns=['HV'])
    underlying_data_hv = underlying_data_hv.reindex(date_list)
    underlying_data_hv = underlying_data_hv.dropna(subset=['HV'])
    return underlying_data_hv


def get_iv_brent_improved(option_code):
    import numpy as np
    from scipy.stats import norm
    from scipy.optimize import root_scalar
    from datetime import datetime
    import pandas as pd
    import QuantLib as ql
    from xtquant import xtdata
    import logging

    # ������־
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Black-Scholes���ۺ���
    def bs_price(S, K, T, r, sigma, opt_type):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if opt_type == 'call':
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # �Ľ������������ʼ���
    def implied_vol_brent_improved(C_market, S, K, T, r, opt_type):
        def objective(sigma):
            return bs_price(S, K, T, r, sigma, opt_type) - C_market

        try:
            # �ȳ��Ա�׼��Χ
            result = root_scalar(objective, bracket=[0.001, 10], method='brentq')
            if result.converged:
                return result.root

            # ʧ�ܺ�������Χ
            result = root_scalar(objective, bracket=[0.0001, 20], method='brentq')
            return result.root if result.converged else np.nan

        except Exception as e:
            logger.error(f"����ʧ��: {str(e)} | S={S}, K={K}, T={T}, r={r}, C={C_market}")
            return np.nan

    try:
        # ��ȡ��Ȩ����
        xtdata.download_history_contracts()
        option_info = xtdata.get_option_detail_data(option_code)
        expire_date = datetime.strptime(option_info['ExpireDate'], '%Y%m%d').date()
        object_code = f"{option_info['OptUndlCode']}.{option_info['OptUndlMarket']}"

        # �������ݣ�������Ի��ƣ�
        max_retries = 3
        for attempt in range(max_retries):
            try:
                xtdata.download_history_data(option_code, period="1d")
                option_data = xtdata.get_market_data_ex([], [option_code], period='1d',
                                                        start_time='', end_time='', count=-1,
                                                        dividend_type='front', fill_data=True)[option_code]
                xtdata.download_history_data(object_code, period='1d',
                                             start_time=option_info['OpenDate'],
                                             end_time=option_info['ExpireDate'])
                object_data = xtdata.get_market_data_ex([], [object_code], period='1d',
                                                        start_time=option_info['OpenDate'],
                                                        end_time=option_info['ExpireDate'],
                                                        count=-1,
                                                        dividend_type='none',
                                                        fill_data=True)[object_code]
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1)

        # ��ʼ�����
        date_list = option_data.index.to_list()
        iv_df = pd.DataFrame(index=date_list, columns=['IV'])
        iv_df_val = pd.DataFrame(index=date_list,
                                 columns=['C_market', 'S', 'K', 'T', 'r', 'intrinsic', 'status'])
        print(object_data['close'])
        print(object_data['close'])
        # ��������
        opt_type = 'call' if option_info['optType'].upper() == 'CALL' else 'put'
        K = option_info['OptExercisePrice']
        r = option_info['OptUndlRiskFreeRate']
        q = 0  # �����޹�Ϣ

        for date in date_list:
            try:
                # ���ڴ���
                date_time = datetime.strptime(date, '%Y%m%d').date()
                today = ql.Date(date_time.day, date_time.month, date_time.year)
                expiry = ql.Date(expire_date.day, expire_date.month, expire_date.year)
                ql.Settings.instance().evaluationDate = today

                if today >= expiry:
                    iv_df_val.loc[date, 'status'] = 'expired'
                    continue

                # ��ȡ�г��۸�
                S = object_data.loc[date, 'close']
                option_price = option_data.loc[date, 'close']

                # ������֤
                if pd.isna(S) or S <= 0 or pd.isna(option_price) or option_price <= 0:
                    iv_df_val.loc[date, 'status'] = 'invalid_price'

                # ����ʱ���ֵ�����ڼ�ֵ
                day_counter = ql.Actual365Fixed()
                T = day_counter.yearFraction(today, expiry)

                if opt_type == 'call':
                    intrinsic = max(S - K, 0)
                else:
                    intrinsic = max(K * np.exp(-r * T) - S, 0)  # ��������

                iv_df_val.loc[date, ['C_market', 'S', 'K', 'T', 'r', 'intrinsic']] = \
                    [option_price, S, K, T, r, intrinsic]

                # �۸�����Լ��
                if option_price < intrinsic - 1e-6:
                    logger.warning(f"{date}: �۸�������ڼ�ֵ ({option_price} < {intrinsic:.6f})")
                    iv_df_val.loc[date, 'status'] = 'below_intrinsic'
                    continue

                # ��������������
                iv = implied_vol_brent_improved(option_price, S, K, T, r, opt_type)

                if np.isnan(iv):
                    iv_df_val.loc[date, 'status'] = 'calc_failed'
                else:
                    iv_df.loc[date, 'IV'] = iv
                    iv_df_val.loc[date, 'status'] = 'success'

            except Exception as e:
                logger.error(f"���� {date} ʱ����: {str(e)}")
                iv_df_val.loc[date, 'status'] = 'error'

        return iv_df, iv_df_val

    except Exception as e:
        logger.error(f"��ʼ��ʧ��: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()


def get_iv(option_code):
    import time
    xtdata.download_history_contracts()
    option_info = xtdata.get_option_detail_data(option_code)
    expire_date = datetime.strptime(option_info['ExpireDate'], '%Y%m%d').date()
    time.sleep(1)
    object_code = option_info['OptUndlCode'] + '.' + option_info['OptUndlMarket']
    xtdata.download_history_data(option_code, period="1d")
    option_data = xtdata.get_market_data_ex([], [option_code], period='1d', start_time='', end_time='', count=-1,
                                            dividend_type='front', fill_data=True)
    option_data = option_data[option_code]
    xtdata.subscribe_quote(object_code, period='1d', start_time=option_info['OpenDate'],
                           end_time=option_info['ExpireDate'], count=-1, callback=None)
    xtdata.download_history_data(object_code, period='1d', start_time=option_info['OpenDate'],
                                 end_time=option_info['ExpireDate'])
    object_data = xtdata.get_market_data_ex(field_list=[], stock_list=[object_code], period='1d',
                                            start_time=option_info['OpenDate'], end_time=option_info['ExpireDate'],
                                            count=-1, dividend_type='none', fill_data=True)
    object_data = object_data[object_code]
    date_list = option_data.index.to_list()
    iv_df = pd.DataFrame(index=date_list, columns=['IV'])

    opt_type = option_info['optType']

    if opt_type.upper() == 'CALL':
        opt_type = ql.Option.Call
    elif opt_type.upper() == 'PUT':
        opt_type = ql.Option.Put
    strike_price = option_info['OptExercisePrice']
    risk_free = option_info['OptUndlRiskFreeRate']
    dividend = 0  # Assuming no dividend
    r = option_info['OptUndlRiskFreeRate']  # �껯���ʣ�������Ȼ�գ�
    K = option_info['OptExercisePrice']

    for date in date_list:
        # 1. �������ںͲ���
        date_time = datetime.strptime(date, '%Y%m%d').date()
        today = ql.Date(date_time.day, date_time.month, date_time.year)
        expiry = ql.Date(expire_date.day, expire_date.month, expire_date.year)
        ql.Settings.instance().evaluationDate = today

        if today >= expiry:
            print(f"Skipping {date}: option expired")
            continue

        # ʹ����Ȼ���껯��׼��Actual/365��
        day_counter = ql.Actual365Fixed()

        # ��������

        q = 0  # �껯��Ϣ�ʣ�������Ȼ�գ�

        # 2. ������Ȩ����
        S = object_data.loc[date]['close']
        sigma = 0.20  # ��ʼ��
        option_price = option_data.loc[date]['close']
        if pd.isna(S) or S <= 0 or pd.isna(option_price) or option_price <= 0:
            print(f"{date}: ��Ч�۸�(S={S}, option={option_price})")
            continue

        T = day_counter.yearFraction(today, expiry)
        intrinsic = max(S - K * np.exp(-r * (T / 365)), 0) if opt_type == ql.Option.Call else max(
            K * np.exp(T / 365) - S, 0)
        if S < intrinsic:
            print(f"{date}: �۸�{option_price}�������ڼ�ֵ{intrinsic}")

        # 3. ������Ȩ����
        exercise = ql.EuropeanExercise(expiry)
        payoff = ql.PlainVanillaPayoff(opt_type, K)
        option = ql.VanillaOption(payoff, exercise)

        # 4. �����г�����
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(S))

        # ʹ����Ȼ��������������
        yield_curve = ql.FlatForward(today, r, day_counter)
        dividend_yield = ql.FlatForward(today, q, day_counter)
        volatility_curve = ql.BlackConstantVol(today, ql.NullCalendar(), sigma, day_counter)

        # 5. ����BSM����
        process = ql.BlackScholesMertonProcess(
            spot_handle,
            ql.YieldTermStructureHandle(dividend_yield),
            ql.YieldTermStructureHandle(yield_curve),
            ql.BlackVolTermStructureHandle(volatility_curve)
        )

        # 6. ��������������
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        iv = option.impliedVolatility(option_price, process, 1e-4, 100, 0.01, 2.0, Bisection())

        iv_df.loc[date, 'IV'] = iv

    return iv_df


def get_option_code(C, market, data_type=2):
    '''

    ToDo:ȡ��ָ��market����Ȩ��Լ

    Args:
        market: Ŀ���г��������н����� IF

    data_type: �������ݷ�Χ���ɷ��������к�Լ��Ĭ�Ͻ����ص�ǰ

        0: ����ǰ
        1: ����ʷ
        2: ��ʷ + ��ǰ

    '''
    _history_sector_dict = {
        "IF": "�����н���",
        "SF": "����������",
        "DF": "���ڴ�����",
        "ZF": "����֣����",
        "INE": "������Դ����",
        "SHO": "������֤��Ȩ",
        "SZO": "������֤��Ȩ",
    }

    # _now_secotr_dict = {
    #     "IF":"�н���",
    #     "SF":"������",
    #     "DF":"������",
    #     "ZF":"֣����",
    #     "INE":"��Դ����",
    #     "SHO":"��֤��Ȩ",
    #     "SZO":"��֤��Ȩ",
    # }

    _sector = _history_sector_dict.get(market)
    # _now_sector = _now_secotr_dict.get(market)
    if _sector == None:
        raise KeyError(f"�����ڸ��г�:{market}")
    _now_sector = _sector[2:]

    # ������֤�͹�����֤��ר�ŵİ�飬����Ҫ����
    if market == "SHO" or market == "SZO":
        if data_type == 0:
            _list = C.get_stock_list_in_sector(_now_sector)
        elif data_type == 1:
            _list = C.get_stock_list_in_sector(_sector)
        elif data_type == 2:
            _list = C.get_stock_list_in_sector(_sector) + C.get_stock_list_in_sector(_now_sector)
        else:
            raise KeyError(f"data_type��������:{data_type}")
        return _list

    # �ڻ���Ȩ��Ҫ���⴦��
    if data_type == 0:
        all_list = C.get_stock_list_in_sector(_now_sector)
    elif data_type == 1:
        all_list = C.get_stock_list_in_sector(_sector)
    elif data_type == 2:
        all_list = C.get_stock_list_in_sector(_sector) + C.get_stock_list_in_sector(_now_sector)
    else:
        raise KeyError(f"data_type��������:{data_type}")

    _list = []
    pattern1 = r'^[A-Z]{2}\d{4}-[A-Z]-\d{4}\.[A-Z]+$'
    pattern2 = r'^[a-zA-Z]+\d+[a-zA-Z]\d+\.[A-Z]+$'
    pattern3 = r'^[a-zA-Z]+\d+-[a-zA-Z]-\d+\.[A-Z]+$'
    for i in all_list:
        import re
        if re.match(pattern1, i):
            _list.append(i)
        elif re.match(pattern2, i):
            _list.append(i)
        elif re.match(pattern3, i):
            _list.append(i)
    # _list =[i for i in all_list if re.match(pattern, i)]
    return _list


def run_strategy(user_script: str, param: dict):
    try:
        from xtquant.qmttools import run_strategy_file
        ret = run_strategy_file(user_script, param)
        print(ret)
        return ret
    except Exception as e:
        print(e)
    return


def init(C):
    # try:
    #     g.sector_list = ["SZO", "SHO", "INE", "ZF", "DF", "SF", "IF"]
    #     g.opt_code_dict = {}
    #     for sector in g.sector_list:
    #         g.opt_code_dict[sector] = get_option_code(C, sector)
    # except Exception as e:
    #     print("���� ", e)

    return


def after_init(C):
    # try:
    #     iv_data = []
    #     for params in iv_param_lists:
    #         try:
    #             iv = ContextInfo.bsm_price(
    #                 C,
    #                 optType=params["optionType"],
    #                 targetPrice=params["objectPrice"],
    #                 strikePrice=params["strikePrice"],
    #                 riskFree=params["riskFreeRate"],
    #                 sigma=None,  # ���� IV ��������Ȩ�۸�
    #                 days=params["timeToExpiry"],
    #                 dividend=params["dividend"]
    #             )
    #             iv_data.append({"date": params["date"], "IV": iv})
    #         except Exception as e:
    #             print(f"Error calculating IV for {params['date']}: {str(e)}")
    #             iv_data.append({"date": params["date"], "IV": None})
    #
    #     g.iv_df = pd.DataFrame(iv_data).set_index("date")

    return

    # print(xtdata.get_market_data_ex(field_list=[], stock_list=[opt_code], period='1d', start_time='',
    #                                 end_time='', count=-1,
    #                                 dividend_type='none', fill_data=True)[opt_code].columns)

    # for i in g.opt_code_dict:
    #     xtdata.download_history_data(i, period='1d', start_time='', end_time='')
    #     xtdata.get_market_data_ex(field_list=[], stock_list=i, period='1d', start_time='', end_time='', count=-1,
    #                               dividend_type='none', fill_data=True)
    # except Exception as e:
    #     print('����', e)
    # pass


if __name__ == '__main__':
    import sys

    user_script = sys.argv[0]
    #
    # param_list = [{
    #     'stock_code': '399852.SZ',
    #     'period': '1d',
    #
    # }]
    # lock = mp.Manager().Lock()
    # for i in range(len(param_list)):
    #     run_strategy(user_script, param_list[i])

    xtdata.download_history_data(g.option_code, period="1d")
    opt_data = xtdata.get_market_data_ex(field_list=[], stock_list=[g.option_code], period='1d',
                                         count=-1, dividend_type='none', fill_data=True)[g.option_code]

    date_list = opt_data.index.to_list()
    date_list = [str(d) for d in date_list]
    opt_code_hv = get_hv(g.option_code)
    opt_code_iv, opt_code_iv_val = get_iv_brent_improved(g.option_code)
    print(opt_code_iv.dropna(), "\n", opt_code_iv_val)
    plt_output(opt_code_hv, opt_code_iv.fillna(0), title=g.option_code)
