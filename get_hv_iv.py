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
    """绘制历史波动率(HV)和隐含波动率(IV)并保存图表"""
    # 设置支持中文的字体
    plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "sans-serif"]

    plt.figure(figsize=(14, 7))

    # 绘制历史波动率(HV)
    if isinstance(hv_data, pd.DataFrame) and 'HV' in hv_data.columns:
        plt.plot(hv_data.index, hv_data['HV'], label='历史波动率(HV)', linewidth=2, color='blue')
    else:
        print("警告: HV数据格式不正确或缺少'HV'列")

    # 绘制隐含波动率(IV)
    if isinstance(iv_data, pd.DataFrame) and 'IV' in iv_data.columns:
        plt.plot(iv_data.index, iv_data['IV'], label='隐含波动率(IV)', linewidth=2, color='red')
    else:
        print("警告: IV数据格式不正确或缺少'IV'列")

    plt.title(f'{title} 波动率分析')
    plt.xlabel('日期')
    plt.ylabel('波动率')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best')  # 显示图例
    # 优化日期显示
    ax = plt.gca()
    # date_format = mdates.DateFormatter('%Y-%m-%d')
    # ax.xaxis.set_major_formatter(date_format)

    if max_date_ticks > 0:
        ax.xaxis.set_major_locator(plt.MaxNLocator(max_date_ticks))
    # 自动旋转日期标签避免重叠
    plt.xticks(rotation=45)
    plt.tight_layout()  # 确保标签和标题不被裁剪
    plt.show()


def get_hv(opt_code, rolling_window=20):
    def calculate_hv(df, window=20):
        """
        基于标的资产收盘价计算历史波动率
        :param df: 标的的dataframe，需包含'close'和'preClose'列
        :param window: 滚动窗口(交易日)
        :return: 包含HV列的DataFrame
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

    # 截取日期
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

    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Black-Scholes定价函数
    def bs_price(S, K, T, r, sigma, opt_type):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if opt_type == 'call':
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # 改进的隐含波动率计算
    def implied_vol_brent_improved(C_market, S, K, T, r, opt_type):
        def objective(sigma):
            return bs_price(S, K, T, r, sigma, opt_type) - C_market

        try:
            # 先尝试标准范围
            result = root_scalar(objective, bracket=[0.001, 10], method='brentq')
            if result.converged:
                return result.root

            # 失败后尝试扩大范围
            result = root_scalar(objective, bracket=[0.0001, 20], method='brentq')
            return result.root if result.converged else np.nan

        except Exception as e:
            logger.error(f"计算失败: {str(e)} | S={S}, K={K}, T={T}, r={r}, C={C_market}")
            return np.nan

    try:
        # 获取期权数据
        xtdata.download_history_contracts()
        option_info = xtdata.get_option_detail_data(option_code)
        expire_date = datetime.strptime(option_info['ExpireDate'], '%Y%m%d').date()
        object_code = f"{option_info['OptUndlCode']}.{option_info['OptUndlMarket']}"

        # 下载数据（添加重试机制）
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

        # 初始化结果
        date_list = option_data.index.to_list()
        iv_df = pd.DataFrame(index=date_list, columns=['IV'])
        iv_df_val = pd.DataFrame(index=date_list,
                                 columns=['C_market', 'S', 'K', 'T', 'r', 'intrinsic', 'status'])
        print(object_data['close'])
        print(object_data['close'])
        # 参数设置
        opt_type = 'call' if option_info['optType'].upper() == 'CALL' else 'put'
        K = option_info['OptExercisePrice']
        r = option_info['OptUndlRiskFreeRate']
        q = 0  # 假设无股息

        for date in date_list:
            try:
                # 日期处理
                date_time = datetime.strptime(date, '%Y%m%d').date()
                today = ql.Date(date_time.day, date_time.month, date_time.year)
                expiry = ql.Date(expire_date.day, expire_date.month, expire_date.year)
                ql.Settings.instance().evaluationDate = today

                if today >= expiry:
                    iv_df_val.loc[date, 'status'] = 'expired'
                    continue

                # 获取市场价格
                S = object_data.loc[date, 'close']
                option_price = option_data.loc[date, 'close']

                # 数据验证
                if pd.isna(S) or S <= 0 or pd.isna(option_price) or option_price <= 0:
                    iv_df_val.loc[date, 'status'] = 'invalid_price'

                # 计算时间价值和内在价值
                day_counter = ql.Actual365Fixed()
                T = day_counter.yearFraction(today, expiry)

                if opt_type == 'call':
                    intrinsic = max(S - K, 0)
                else:
                    intrinsic = max(K * np.exp(-r * T) - S, 0)  # 修正这里

                iv_df_val.loc[date, ['C_market', 'S', 'K', 'T', 'r', 'intrinsic']] = \
                    [option_price, S, K, T, r, intrinsic]

                # 价格合理性检查
                if option_price < intrinsic - 1e-6:
                    logger.warning(f"{date}: 价格低于内在价值 ({option_price} < {intrinsic:.6f})")
                    iv_df_val.loc[date, 'status'] = 'below_intrinsic'
                    continue

                # 计算隐含波动率
                iv = implied_vol_brent_improved(option_price, S, K, T, r, opt_type)

                if np.isnan(iv):
                    iv_df_val.loc[date, 'status'] = 'calc_failed'
                else:
                    iv_df.loc[date, 'IV'] = iv
                    iv_df_val.loc[date, 'status'] = 'success'

            except Exception as e:
                logger.error(f"处理 {date} 时出错: {str(e)}")
                iv_df_val.loc[date, 'status'] = 'error'

        return iv_df, iv_df_val

    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
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
    r = option_info['OptUndlRiskFreeRate']  # 年化利率（基于自然日）
    K = option_info['OptExercisePrice']

    for date in date_list:
        # 1. 设置日期和参数
        date_time = datetime.strptime(date, '%Y%m%d').date()
        today = ql.Date(date_time.day, date_time.month, date_time.year)
        expiry = ql.Date(expire_date.day, expire_date.month, expire_date.year)
        ql.Settings.instance().evaluationDate = today

        if today >= expiry:
            print(f"Skipping {date}: option expired")
            continue

        # 使用自然日年化基准（Actual/365）
        day_counter = ql.Actual365Fixed()

        # 参数设置

        q = 0  # 年化股息率（基于自然日）

        # 2. 定义期权数据
        S = object_data.loc[date]['close']
        sigma = 0.20  # 初始化
        option_price = option_data.loc[date]['close']
        if pd.isna(S) or S <= 0 or pd.isna(option_price) or option_price <= 0:
            print(f"{date}: 无效价格(S={S}, option={option_price})")
            continue

        T = day_counter.yearFraction(today, expiry)
        intrinsic = max(S - K * np.exp(-r * (T / 365)), 0) if opt_type == ql.Option.Call else max(
            K * np.exp(T / 365) - S, 0)
        if S < intrinsic:
            print(f"{date}: 价格{option_price}低于内在价值{intrinsic}")

        # 3. 构建期权对象
        exercise = ql.EuropeanExercise(expiry)
        payoff = ql.PlainVanillaPayoff(opt_type, K)
        option = ql.VanillaOption(payoff, exercise)

        # 4. 设置市场环境
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(S))

        # 使用自然日算器构建曲线
        yield_curve = ql.FlatForward(today, r, day_counter)
        dividend_yield = ql.FlatForward(today, q, day_counter)
        volatility_curve = ql.BlackConstantVol(today, ql.NullCalendar(), sigma, day_counter)

        # 5. 构建BSM过程
        process = ql.BlackScholesMertonProcess(
            spot_handle,
            ql.YieldTermStructureHandle(dividend_yield),
            ql.YieldTermStructureHandle(yield_curve),
            ql.BlackVolTermStructureHandle(volatility_curve)
        )

        # 6. 计算隐含波动率
        option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
        iv = option.impliedVolatility(option_price, process, 1e-4, 100, 0.01, 2.0, Bisection())

        iv_df.loc[date, 'IV'] = iv

    return iv_df


def get_option_code(C, market, data_type=2):
    '''

    ToDo:取出指定market的期权合约

    Args:
        market: 目标市场，比如中金所填 IF

    data_type: 返回数据范围，可返回已退市合约，默认仅返回当前

        0: 仅当前
        1: 仅历史
        2: 历史 + 当前

    '''
    _history_sector_dict = {
        "IF": "过期中金所",
        "SF": "过期上期所",
        "DF": "过期大商所",
        "ZF": "过期郑商所",
        "INE": "过期能源中心",
        "SHO": "过期上证期权",
        "SZO": "过期深证期权",
    }

    # _now_secotr_dict = {
    #     "IF":"中金所",
    #     "SF":"上期所",
    #     "DF":"大商所",
    #     "ZF":"郑商所",
    #     "INE":"能源中心",
    #     "SHO":"上证期权",
    #     "SZO":"深证期权",
    # }

    _sector = _history_sector_dict.get(market)
    # _now_sector = _now_secotr_dict.get(market)
    if _sector == None:
        raise KeyError(f"不存在该市场:{market}")
    _now_sector = _sector[2:]

    # 过期上证和过期深证有专门的板块，不需要处理
    if market == "SHO" or market == "SZO":
        if data_type == 0:
            _list = C.get_stock_list_in_sector(_now_sector)
        elif data_type == 1:
            _list = C.get_stock_list_in_sector(_sector)
        elif data_type == 2:
            _list = C.get_stock_list_in_sector(_sector) + C.get_stock_list_in_sector(_now_sector)
        else:
            raise KeyError(f"data_type参数错误:{data_type}")
        return _list

    # 期货期权需要额外处理
    if data_type == 0:
        all_list = C.get_stock_list_in_sector(_now_sector)
    elif data_type == 1:
        all_list = C.get_stock_list_in_sector(_sector)
    elif data_type == 2:
        all_list = C.get_stock_list_in_sector(_sector) + C.get_stock_list_in_sector(_now_sector)
    else:
        raise KeyError(f"data_type参数错误:{data_type}")

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
    #     print("报错： ", e)

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
    #                 sigma=None,  # 计算 IV 而不是期权价格
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
    #     print('报错：', e)
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
