# coding:GBK
import concurrent.futures as con
import datetime
import multiprocessing as mp
import sys
import traceback

import pandas as pd
from xtquant import xtdata
from xtquant.qmttools.functions import get_trade_detail_data, passorder
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
        symbol = 'IF00.IF'  # 合约需要是主连合约
        period = "historymaincontract"  # period需指定为 "historymaincontract"
        # 下载历史主力合约
        xtdata.download_history_data(symbol, period, '', '')  # 获取之前需要先下载到本地

        xtdata.get_market_data_ex([], stock_list=[symbol], period='1d', start_time='', end_time='', count=-1,
                                  dividend_type='none', fill_data=True)

    except Exception as e:
        print(e)
        traceback.print_exc()
    return


def handlebar(C):
    target = 'IF00.IF'
    try:
        print('1' * 70)
        passorder(0, 1101, 'test', target, 5, 5, 10, 1, "test_trade",
                  datetime.datetime.now().strftime('%Y%m%d%H%M%S'), C)
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
        'stock_code': '000300.SH',  # 驱动handlebar的代码,
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

