# coding:GBK
import xtquant.xtdata as xtdata
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

xtdata.reconnect(port=58610)
xtdata.enable_hello = False


def split_trading_day_into_segments(segment_minutes=30):
    """��ÿ�������յĽ���ʱ�仮��Ϊ���ʱ��"""
    """��ʱ���ô�"""

    # segments = []
    #
    # # ����ʱ�� (9:30-11:30)
    # morning_start = datetime.strptime("0930", "%H%M")
    # morning_end = datetime.strptime("1130", "%H%M")
    #
    # # ����ʱ�� (13:00-15:00)
    # afternoon_start = datetime.strptime("1300", "%H%M")
    # afternoon_end = datetime.strptime("1500", "%H%M")
    #
    # # ���������ʱ��
    # current_time = morning_start
    # while current_time < morning_end:
    #     segment_end = min(current_time + timedelta(minutes=segment_minutes), morning_end)
    #     segments.append((current_time.strftime("%H%M"), segment_end.strftime("%H%M")))
    #     current_time = segment_end
    #
    # # ���������ʱ��
    # current_time = afternoon_start
    # while current_time < afternoon_end:
    #     segment_end = min(current_time + timedelta(minutes=segment_minutes), afternoon_end)
    #     segments.append((current_time.strftime("%H%M"), segment_end.strftime("%H%M")))
    #     current_time = segment_end
    #
    # print(segments)
    segments = [('0930', '1000'), ('1300', '1330'), ('1430', '1500')]
    return segments

#��k��
def get_kline(stock_list):
    global segment_benefits, segments_market_data
    xtdata.download_history_data2(stock_list, '5m', start_time='20230101', end_time='20230718')
    try:
        segments_market_data = xtdata.get_market_data_ex(
            ['open', 'high', 'low', 'close', 'volume', 'amount'],  # ȷ���ֶΰ���volume��amount
            stock_list,
            period='30m',
            start_time='20230101',
            end_time='20230718'
        )
        print("�ɹ���ȡK������")

    except Exception as e:
        print(f"��ȡK������ʧ��: {e}")
    return segments_market_data


def get_segments_return(segments_market_data, segment: tuple):
    segment_returns = pd.DataFrame()
    for code, df in segments_market_data.items():
        try:
            df = df.copy()
            df = df.sort_index()
            date_part = df.index.str[-6:]
            mask = (date_part == segment[0]) | (date_part == segment[1])
            df_filtered = df[mask].sort_index()
            df_filtered['segment_return'] = (df_filtered['close'] - df_filtered['open'].shift(1))/df_filtered['open'].shift(1)
            date_part = df_filtered.index.str[-6:]
            mask = (date_part == segment[1])
            df_filtered = df_filtered[mask].sort_index()
            segment_returns = df_filtered[['segment_return']].copy()
            print(segment_returns.items())
        except Exception as e:
            print(f'�����ˣ� {code}, {e}')
            return
    return segment_returns


def plt_output(df, column):
    """��ͼ��
        param:
        df dataframe���
        column ��ͼ��Ӧ����
        return��
        ��Ļ���������ͼ
    """
    plt.plot(df.index, column, label='�ۼƾ�ֵ', linewidth=2)
    plt.title('title')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.show()
    return


# ʾ��ʹ��
if __name__ == "__main__":
    IH = "000300.SH"
    sz50 = "000016.SH"
    IF = ""
    hs300 = "000300.SH"
    zz500 = "000905.SH"
    zz1000 = "000852.SH"
    stock_list = IH

    segments = [('0930', '1000'), ('1300', '1330'), ('1430', '1500'), ('1500', '0930')]

    segments_market_data = get_kline(stock_list)
    segment_returns = get_segments_return(segments_market_data, ('100000', '150000'))

    # �����ۼƾ�ֵ ��������Ϊ��close - open��/open, �ۼ�������ΪV0*(1+ri)*...*(1+r1)
    segment_returns['net_value'] = (1 + segment_returns['segment_return']).cumprod()

    print(segment_returns)
    plt_output(segment_returns, segment_returns['net_value'])


