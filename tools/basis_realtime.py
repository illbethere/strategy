import time
from datetime import date
import pandas as pd

from xtquant import xtdata
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from xtquant import xtdatacenter as xtdc
xtdc.set_token('4065054877ce5724155dbc5bcba200381ce5eb35')
xtdc.init()


def plt_output(df, max_time_ticks=20, show=True):
    """
    Visualize futures vs underlying price and basis data

    Args:
    df: DataFrame containing columns 'close', 'obj_close', and 'basis'
    max_time_ticks: Maximum number of time ticks on x-axis
    show: Whether to display the chart (set False for background generation)
    """
    # Clear previous figure if exists
    plt.clf()  # Clear current figure
    plt.close()  # Close previous figure

    # Create figure and primary axis
    fig, ax1 = plt.subplots(figsize=(14, 7))
    df = df.copy()
    df.index = (df.index.astype(str).str[-6:-4] + ':' +
                df.index.astype(str).str[-4:-2])

    # Plot close and obj_close on left y-axis
    if 'close' in df.columns:
        ax1.plot(df.index, df['close'], label='Futures Price', linewidth=2, color='blue')
    if 'obj_close' in df.columns:
        ax1.plot(df.index, df['obj_close'], label='Underlying Price', linewidth=2, color='red')
    if 'etf_close' in df.columns:
        ax1.plot(df.index, df['etf_close'], label='etf Price', linewidth=2, color='green')

    ax1.set_xlabel('Time')
    ax1.set_ylabel('Price')
    ax1.grid(True, linestyle='--', alpha=0.7)

    # Create secondary y-axis for basis
    ax2 = ax1.twinx()
    if 'basis' in df.columns:
        ax2.plot(df.index, df['basis'], label='Basis', linewidth=2, color='black')
        ax2.set_ylabel('Basis')

    # Title and legend
    plt.title('Futures vs Underlying (Basis)')
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')

    if max_time_ticks > 0:
        ax1.xaxis.set_major_locator(ticker.MaxNLocator(max_time_ticks))
    plt.xticks(rotation=45)


    plt.tight_layout()

    if show:
        plt.show()
        plt.pause(0.1)  # Allow time for rendering
    else:
        plt.savefig('./', dpi=300, bbox_inches="tight")
        plt.close()

    return fig, (ax1, ax2)  # Return figure and axes for further customization


symbol = "IM2506.IF"
index_code = '000852.SH'
etf_code = '516300.SH'
today = date.today()
current_pandas_time = pd.Timestamp.now()
current_time = current_pandas_time.strftime('%H%M%S')
today_open = today.strftime("%Y%m%d") + '093000'
today_close = today.strftime("%Y%m%d") + '150000'
xtdata.subscribe_quote(symbol, period='1m', count=-1, start_time=today_open)
xtdata.subscribe_quote(index_code, period='1m', count=-1, start_time=today_open)
xtdata.subscribe_quote(etf_code, period='1m', count=-1, start_time=today_open)
while True:
    data = xtdata.get_market_data_ex(['close'], [symbol, index_code, etf_code], period='1m', count=-1)
    fut_data, obj_data, etf_data= data[symbol], data[index_code], data[etf_code]
    etf_data['close'] = etf_data['close'] * 2500
    fut_data['close'] = fut_data['close']
    df_merged = pd.concat([
        fut_data.rename(columns={'close': 'close'}),
        obj_data.rename(columns={'close': 'obj_close'}),
        etf_data.rename(columns={'close': 'etf_close'})], axis=1)
    df_merged['basis'] = df_merged['close'] - df_merged['obj_close']
    plt_output(df_merged, current_time != df_merged.index[-1][-6:])
    if current_time == df_merged.index[-1][-6:]:
        break
    time.sleep(60)

