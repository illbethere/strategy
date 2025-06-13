# coding:GBK
import time

import xtquant.xtdata as xtdata
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

# xtdata.reconnect(port=58610)
# xtdata.enable_hello = False

def plt_output(equity, max_time_ticks=20):
    plt.rcParams["font.family"] = ["sans-serif"]

    plt.figure(figsize=(14, 7))

    if isinstance(equity, pd.DataFrame) and 'equity' in equity.columns:
        plt.plot(equity['open_time'], equity['equity'], label='equity', linewidth=2, color='blue')
    else:
        print(" error: 'equity' ")

    plt.title(f'equity')
    plt.xlabel('time')
    plt.ylabel('equity')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best') 
    ax = plt.gca()
    # date_format = mdates.DateFormatter('%Y-%m-%d')
    # ax.xaxis.set_major_formatter(date_format)

    if max_time_ticks > 0:
        ax.xaxis.set_major_locator(plt.MaxNLocator(max_time_ticks))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# 示例使用
if __name__ == "__main__":
    # xtdata.get_trading_dates('IF', start_time='', end_time='', count=-1)
    # instrument_code = 'IF2506.CFFEX'
    # instrument_info = xtdata.get_instrument_detail(instrument_code)
    # print(instrument_info)
    # instrument_market_code = instrument_info['ExchangeCode'] + '.' + instrument_info['ProductID']
    # xtdata.download_history_data(instrument_market_code, period="1d")
    # option_data = xtdata.get_market_data_ex([], [instrument_market_code], period='1d', start_time='', end_time='',
    #                                         count=-1, dividend_type='front', fill_data=True)
    # # object_code =
    # option_data = option_data[option_code]
    # xtdata.subscribe_quote(object_code, period='1d', start_time=instrument_info['OpenDate'],
    #                        end_time=instrument_info['ExpireDate'], count=-1, callback=None)
    # xtdata.download_history_data(object_code, period='1d', start_time=instrument_info['OpenDate'],
    #                              end_time=instrument_info['ExpireDate'])
    # object_data = xtdata.get_market_data_ex(field_list=[], stock_list=[object_code], period='1d',
    #                                         start_time=instrument_info['OpenDate'], end_time=instrument_info['ExpireDate'],
    #                                         count=-1, dividend_type='none', fill_data=True)
    # print(option_data)
    df = pd.read_pickle('df.pkl')
    print(df)
    plt_output(df)

