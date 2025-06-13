import pandas as pd
from xtquant import xtdata
import numpy as np
from datetime import datetime, date, timedelta,time
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

xtdata.reconnect(port=58610)
xtdata.enable_hello = False

import pandas as pd


import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

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
                df.index.astype(str).str[-4:-2] + ':' +
                df.index.astype(str).str[-2:])


    # Plot close and obj_close on left y-axis
    if 'close' in df.columns:
        ax1.plot(df.index, df['close'], label='Futures Price', linewidth=2, color='blue')
    if 'obj_close' in df.columns:
        ax1.plot(df.index, df['obj_close'], label='Underlying Price', linewidth=2, color='red')
    if 'etf_close' in df.columns:
        ax1.plot(df.index, df['etf_close'], label='etf Price', linewidth=1, color='green')
    
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
    
    
    # Format time axis
    if max_time_ticks > 0:
        ax1.xaxis.set_major_locator(plt.MaxNLocator(max_time_ticks))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    if show:
        plt.show()
        plt.pause(0.1)  # Allow time for rendering
    
    return fig, (ax1, ax2)  # Return figure and axes for further customization


def get_sharpe_ratio(df, risk_free_rate=0.02):
    """计算夏普比率"""
    # 按日期分组计算每日收益
    daily_returns = df.groupby(pd.to_datetime(df['open_time'].dt.date))['profit'].sum() / \
                    df.groupby(pd.to_datetime(df['open_time'].dt.date))['equity'].first()
    annualized_return = daily_returns.mean() * 252
    annualized_volatility = daily_returns.std() * np.sqrt(252)
    return (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility != 0 else 0

def get_PL_ratio(df):
    """计算盈亏比"""
    total_profit = df[df['profit'] > 0]['profit'].sum()
    total_loss = abs(df[df['profit'] < 0]['profit'].sum())
    return total_profit / total_loss if total_loss != 0 else float('inf')

def get_total_return(df):
    """计算总收益率(%)"""
    initial_equity = df['equity'].iloc[0]
    final_equity = df['equity'].iloc[-1]
    return (final_equity / initial_equity - 1) * 100

def get_annualized_return(df):
    """计算年化收益率"""
    start_date = pd.to_datetime(df['open_time'].iloc[0].date())
    end_date = pd.to_datetime(df['close_time'].iloc[-1].date())
    tra
    trading_days = (end_date - start_date).days
    total_return = get_total_return(df) / 100
    return (1 + total_return) ** (252 / max(1, trading_days)) - 1

def get_win_rate(df):
    """计算胜率"""
    wins = (df['profit'] > 0).sum()
    return wins / len(df) if len(df) > 0 else 0

def get_avg_holding_time(df):
    """计算平均持仓时间(小时)"""
    # 直接使用 DataFrame 中已有的 holding_period 列
    
    return df['holding_period'].mean() if len(df) > 0 else 0

def get_max_drawdown(df):
    """计算相对最大回撤(%)"""
    # 计算累计收益
    df = df.copy()
    df['cumulative'] = df['profit'].cumsum() + df['equity'].iloc[0]
    peaks = df['cumulative'].cummax()
    drawdowns = (peaks - df['cumulative']) / peaks
    return drawdowns.max() * 100

def get_trading_days(start_date, close_date):
    trade_cal = []
    # 格式判断和转换
    if isinstance(start_date, pd.Timestamp):
        start_date = start_date.strftime('%Y%m%d')
    if isinstance(close_date, pd.Timestamp):
        close_date = close_date.strftime('%Y%m%d')
    trade_calendar = pd.read_pickle('trading_calendar.pkl')
    trade_calendar = trade_calendar[0].tolist()
    
    #xt交易日历获取
    if start_date in trade_calendar:
        if close_date in trade_calendar:
            trade_cal = trade_calendar[trade_calendar.index(start_date):trade_calendar.index(close_date) + 1]
    return trade_cal

def get_detail_analyze(df, risk_free_rate=0.02):
    """生成详细的交易分析结果"""
    results = {}
    df = df.copy()

    daily_returns = df.groupby(pd.to_datetime(df['open_time'].dt.date))['profit'].sum() / \
                    df.groupby(pd.to_datetime(df['open_time'].dt.date))['equity'].first()
    annualized_return = daily_returns.mean() * 252
    annualized_volatility = daily_returns.std() * np.sqrt(252)
    results['夏普比率'] = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility != 0 else 0

    total_profit = df[df['profit'] > 0]['profit'].sum()
    total_loss = abs(df[df['profit'] < 0]['profit'].sum())
    results['盈亏比'] = total_profit / total_loss if total_loss != 0 else float('inf')

    initial_equity = df['equity'].iloc[0]
    final_equity = df['equity'].iloc[-1]
    results['总收益率(%)'] =  (final_equity / initial_equity - 1) * 100

    start_date = pd.to_datetime(df['open_time'].min().date())
    end_date = pd.to_datetime(df['close_time'].max().date())
    trading_days = get_trading_days(start_date, end_date)
    total_return = get_total_return(df) / 100
    results['年化收益率'] = "{:.2%}".format(float(((1 + total_return) ** (252 / max(1, len(trading_days)) - 1))))

    wins = (df['profit'] > 0).sum()
    results['胜率'] =  wins / len(df) if len(df) > 0 else 0

    
    # results['平均持仓时间(小时)'] = df['holding_period'].mean() if len(df) > 0 else 0
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    ### 持有时间计算
    holding_times = []
    cal = get_trading_days(df['open_time'].min(), df['close_time'].max())
    for index, row in df.iterrows():
        open_time = row['open_time']  # datetime 对象
        close_time = row['close_time']  # datetime 对象
        
        open_date = open_time.date()
        close_date = close_time.date()
        
        open_date_str = open_date.strftime('%Y%m%d')
        close_date_str = close_date.strftime('%Y%m%d')
        
        try:
            day_during = cal.index(close_date_str) - cal.index(open_date_str)
        except ValueError:
            print(f"日期不在交易日历中: {open_date_str} 或 {close_date_str}")
            continue
        
        # 计算持有时间
        holding_time = timedelta()
        
        # 处理同一天内的交易
        if day_during == 0:
            if close_time.time() <= morning_end:
                holding_time = close_time - open_time
            elif open_time.time() >= afternoon_start:
                holding_time = close_time - open_time
            else:
                morning_part = datetime.combine(open_time.date(), morning_end) - open_time
                afternoon_part = close_time - datetime.combine(close_time.date(), afternoon_start)
                holding_time = morning_part + afternoon_part
        
        # 处理跨天交易
        else:
            first_day_part = datetime.combine(open_time.date(), afternoon_end) - open_time
            last_day_part = close_time - datetime.combine(close_time.date(), morning_start)
            
            if open_time.time() >= afternoon_start:
                first_day_part = datetime.combine(open_time.date(), afternoon_end) - open_time
            elif open_time.time() <= morning_end:
                first_day_part = (datetime.combine(open_time.date(), morning_end) - open_time) + timedelta(hours=1, minutes=30)
            
            if close_time.time() <= morning_end:
                last_day_part = close_time - datetime.combine(close_time.date(), morning_start)
            elif close_time.time() >= afternoon_start:
                last_day_part = close_time - datetime.combine(close_time.date(), afternoon_start)
            
            full_days = day_during - 1
            middle_days_part = timedelta(hours=4, minutes=30) * full_days
            
            holding_time = first_day_part + middle_days_part + last_day_part
        
        # 转换为小时
        holding_hours = round(holding_time.total_seconds() / 3600, 2)
        holding_times.append(holding_hours)

    results['持有时间（H）'] = sum(holding_times)/len(holding_times)
    # for index, row in df.iterrows():
    #     open_date = row['open_time'].date().strftime('%Y%m%d')
    #     open_time = row['open_time'].time()
    #     close_date = row['close_time'].date().strftime('%Y%m%d')
    #     close_time = row['close_time'].time()
    #     day_during = cal.index(close_date) - cal.index(open_date) # + pd.Timedelta(days=1)
    #     print(day_during)
    #     if open_time < time(11,30):
    #         holding_time = close_time - time(0,30)
        # holding_time = close_time - day_during * time(20,30) - max(day_during - 1, 0) * time(1,30) - open_time
        # print(holding_time)
        # results['平均持仓时间(小时)'] = holding_time

    df['cumulative'] = df['profit'].cumsum() + df['equity'].iloc[0]
    peaks = df['cumulative'].cummax()
    drawdowns = (peaks - df['cumulative']) / peaks
    results['相对最大回撤(%)'] = drawdowns.max() * 100
    
    return results

# 使用示例
if __name__ == "__main__":
    # 假设 df 是已经加载好的 DataFrame
    df = pd.read_pickle('df.pkl')
    
    # 计算并打印各项指标
    analysis_results = get_detail_analyze(df)
    print(analysis_results)




