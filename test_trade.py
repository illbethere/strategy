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
    #     # ��ȡ��ֵ����
    #     df = ret.get_backtest_index()[['ʱ��', '��λ��ֵ']]
    #     # ��ȡ C._param �еĲ���n,�滻��λ��ֵ
    #     n1 = param['n1']
    #     n2 = param['n2']
    #     # print(n1,n2)
    #     df.rename(columns={'��λ��ֵ': f'��λ_{n1}_{n2}'}, inplace=True)
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
        symbol = 'IF00.IF'  # ��Լ��Ҫ��������Լ
        period = "historymaincontract"  # period��ָ��Ϊ "historymaincontract"
        # ������ʷ������Լ
        xtdata.download_history_data(symbol, period, '', '')  # ��ȡ֮ǰ��Ҫ�����ص�����

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
        print('������', e)
        traceback.print_exc()
        return
    return


if __name__ == '__main__':
    import sys
    import os

    user_script = sys.argv[0]

    param_list = [{
        'stock_code': '000300.SH',  # ����handlebar�Ĵ���,
        'period': '5m',  # ����ִ������ ����ͼ����
        'start_time': '2024-07-01 00:00:00',  # ע���ʽ����Ҫд��
        'end_time': '2024-07-31 00:00:00',  # ע���ʽ����Ҫд��
        'trade_mode': 'backtest',  # simulation': ģ��, 'trading':ʵ��, 'backtest':�ز�
        'quote_mode': 'history',
        'dividend_type': 'front',
        'asset': 10000000,
        'strategy_name': 'KDJ���Ӳ���',
        'log_path': f'./log/{os.path.basename(user_script)[:-3]}.log',
        'account': 'test'
        # handlebarģʽ��'realtime':��ʵʱ���飨��������ʷ�����handlebar��,'history':����ʷ����, 'all'�����У���history+realtime
    }]
    lock = mp.Manager().Lock()
    with con.ProcessPoolExecutor(max_workers=60) as executor:
        futures = {executor.submit(run_strategy, lock, user_script, param_list[i]): i for i in range(len(param_list))}

