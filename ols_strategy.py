# coding:GBK
import concurrent.futures as con
import multiprocessing as mp
import sys
import traceback

import pandas as pd
from xtquant import xtdata
from xtquant.qmttools.functions import get_trade_detail_data
from xtquant.xtdata import try_except

from myStrategy.tools.order import order_target_weight

sys.path.append('../..')

xtdata.reconnect(port=58610)
xtdata.enable_hello = False


class G():
    pass


g = G()


def run_strategy(lock, user_script: str, param: dict):
    try:
        from xtquant.qmttools import run_strategy_file

        ret = run_strategy_file(user_script, param)
        print(ret)
        return ret
    # print(ret)
    # if ret:
    #     # 提取净值数据
    #     df = ret.get_backtest_index()[['时间', '单位净值']]
    #     # 获取 C._param 中的参数n,替换单位净值
    #     n1 = param['n1']
    #     n2 = param['n2']
    #     # print(n1,n2)
    #     df.rename(columns={'单位净值': f'档位_{n1}_{n2}'}, inplace=True)
    #     return df
    # return None
    except Exception as e:
        print(e)
    return


def calculate_ols(data):
    import pandas as pd

    all_ols = pd.DataFrame()
    for code, df in data.items():
        try:
            df = df.copy()
            if not {'close'}.issubset(df.columns):
                print(f"[跳过] {code} 缺少必要字段")
                continue

            df['date'] = df.index

        except Exception as e:
            print("报错: ", e)
            continue

    top_20 = (
        all_ols.sort_values(['date', 'ols'], ascending=[True, False])
            .groupby('date')
            .head(20)
    )
    daily_top20_list = []
    for date, group in top_20.groupby('date'):
        stock_list = group['code'].tolist()
        daily_top20_list.append({'date': date, 'top20_stocks': stock_list})

    daily_top20_df = pd.DataFrame(daily_top20_list)
    g.daily_top20_df = daily_top20_df.set_index('date').shift(1)
    return


def init(C):
    try:
        C.open_tax = 0
        C.account_id = C._param['account']
        C.min_commission = 0
        g.num = 20
        g.trade_value = C.asset / g.num
        g.trade_weight = 1 / g.num
        g.daily_top20_df = pd.DataFrame()
        g.strategy = 'OLS'
    except Exception as e:
        print(e)
    # g.trade_etf_list = []
    # g.score_df = pd.DataFrame()
    return


def after_init(C):
    try:
        all_kdj = pd.DataFrame()
        code_list = xtdata.get_stock_list_in_sector("中证1000")
        # print(code_list)
        xtdata.download_history_data2(code_list, '1d', start_time='', end_time='')
        market_data = xtdata.get_market_data_ex(
            ['open', 'high', 'low', 'close', 'volume', 'amount'],  # 确保字段包含volume和amount
            code_list,
            period='1d',
            start_time='20240701000000',  # 建议设置具体时间范围如'20250301093000'
            end_time='20240801000000'
        )
        g.daily_top20_df = calculate_kdj(market_data)
    except Exception as e:
        print(e)
        traceback.print_exc()
    return


def handlebar(C):

    # now = xtdata.timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y-%m-%d %H:%M:%S")
    # now_hour = xtdata.timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y%m%d%H%M%S")
    now_date = xtdata.timetag_to_datetime(C.get_bar_timetag(C.barpos), "%Y-%m-%d")
    now_time = xtdata.timetag_to_datetime(C.get_bar_timetag(C.barpos), "%H%M%S")
    total_value = get_trade_detail_data(C.account_id, 'stock', 'ACCOUNT')[0].m_dBalance

    try:
        if now_time == '093500':
            sell_stock_dict = {dt.m_strInstrumentID + '.' + dt.m_strExchangeID: dt.m_dMarketValue for dt in
                               get_trade_detail_data(C.account_id, 'stock', 'position') if dt.m_dMarketValue > 0}
            for stock in sell_stock_dict:
                order_target_weight(stock, 0, 'test', C)
            buy_stocks = g.daily_top20_df.loc[now_date, 'top20_stocks']
            if not isinstance(buy_stocks, float):
                for stock in buy_stocks:
                    order_target_weight(stock, g.trade_weight, 'test', C)
        else:
            pass
    except Exception as e:
        print('报错了', e)
        traceback.print_exc()
        return
    return


if __name__ == '__main__':
    import sys
    import os

    user_script = sys.argv[0]

    param_list = [{
        'stock_code': '399852.SZ',  # 驱动handlebar的代码,
        'period': '5m',  # 策略执行周期 即主图周期
        'start_time': '2024-07-01 00:00:00',  # 注意格式，不要写错
        'end_time': '2024-07-31 00:00:00',  # 注意格式，不要写错
        'trade_mode': 'backtest',  # simulation': 模拟, 'trading':实盘, 'backtest':回测
        'quote_mode': 'history',
        'dividend_type': 'front',
        'asset': 10000000,
        'strategy_name': 'KDJ因子测试',
        'log_path': f'./log/{os.path.basename(user_script)[:-3]}.log',
        'account': 'test'
        # handlebar模式，'realtime':仅实时行情（不调用历史行情的handlebar）,'history':仅历史行情, 'all'：所有，即history+realtime
    }]
    lock = mp.Manager().Lock()
    with con.ProcessPoolExecutor(max_workers=60) as executor:
        futures = {executor.submit(run_strategy, lock, user_script, param_list[i]): i for i in range(len(param_list))}
