#!/usr/bin/env python
import re
import numpy as np
import pandas as pd
from xtquant import xtdata
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import schedule
import time
import gc
import matplotlib

# Set matplotlib backend to TkAgg for interactive display
matplotlib.use('TkAgg')

# Check if running in Jupyter environment
try:
    get_ipython
    IN_JUPYTER = True
except NameError:
    IN_JUPYTER = False

from xtquant import xtdatacenter as xtdc  
xtdc.set_token('4065054877ce5724155dbc5bcba200381ce5eb35')
xtdc.init()

# Enable interactive mode and create figure
plt.ion()
fig, ax = plt.subplots(figsize=(12, 6))

def update_chart():
    today = datetime.now().date().strftime('%Y%m%d')
    contract_code = 'IF2506.IF'
    index_code = '000300.SH'
    
    # Fetch index data
    xtdata.subscribe_quote(index_code, period='1m', start_time=today, end_time=today, count=-1, callback=None)
    df_index = xtdata.get_market_data_ex(
        field_list=['close'], 
        stock_list=[index_code], 
        period='1m', 
        start_time=today, 
        end_time=today, 
        count=-1, 
        dividend_type='none', 
        fill_data=True
    ).get(index_code, pd.DataFrame())
    
    # Fetch contract data
    xtdata.subscribe_quote(contract_code, period='1m', start_time=today, end_time=today, count=-1, callback=None)
    df_contract = xtdata.get_market_data_ex(
        field_list=['close'], 
        stock_list=[contract_code], 
        period='1m', 
        start_time=today, 
        end_time=today, 
        count=-1, 
        dividend_type='none', 
        fill_data=True
    ).get(contract_code, pd.DataFrame())
    
    # Calculate basis and process index
    if df_index.empty or df_contract.empty:
        print("No data received")
        return
    
    df = df_contract['close'] - df_index['close']
    try:
        df.index = pd.to_datetime(df.index, format='%Y%m%d%H%M%S')
    except ValueError:
        print("Invalid index format, unable to convert to datetime")
        return
    
    ax.clear()  # Clear previous plot
    
    # Convert time to minutes since market open
    start_time = df.index[0]
    x_values = [(t - start_time).total_seconds() / 60 for t in df.index]
    
    # Define lunch break time range
    lunch_start = pd.Timestamp(f'{today} 11:30:00')
    lunch_end = pd.Timestamp(f'{today} 13:01:00')
    lunch_end_idx = df.index.searchsorted(lunch_end, side='left')
    
    # Adjust x-values to remove lunch break gap
    x_adjusted = np.array(x_values)
    if lunch_end_idx < len(x_adjusted):
        x_adjusted[lunch_end_idx:] -= 90  # Subtract 90 minutes for post-lunch data
    
    # Plot adjusted data
    ax.plot(
        x_adjusted, 
        df, 
        label='Basis', 
        color='blue', 
        linewidth=1.5, 
        marker='o', 
        markersize=3,
        alpha=0.8
    )
    
    # Generate valid trading time points
    time_ranges = [
        ('09:30:00', '11:30:00'),
        ('13:01:00', '15:00:00')
    ]
    time_points = []
    for tr in time_ranges:
        start = pd.Timestamp(f'{today} {tr[0]}')
        end = pd.Timestamp(f'{today} {tr[1]}')
        valid_times = df.index[(df.index >= start) & (df.index <= end)]
        if not valid_times.empty:
            time_points.extend(pd.date_range(start=valid_times[0], end=valid_times[-1], freq='30min'))
    
    # Deduplicate and sort time points
    time_points = pd.DatetimeIndex(sorted(set(time_points)))
    
    # Calculate adjusted tick positions
    x_ticks = []
    for t in time_points:
        if t >= lunch_end:
            x_ticks.append((t - start_time).total_seconds()/60 - 90)
        else:
            x_ticks.append((t - start_time).total_seconds()/60)
    
    # Configure axes
    ax.set_title('Basis Trend (Continuous Trading)', fontsize=14)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Basis Value', fontsize=12)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([t.strftime('%H:%M') for t in time_points], rotation=45, ha='right')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    
    # Add last value annotation
    if not df.empty:
        last_x = x_adjusted[-1]
        last_y = df.iloc[-1]
        ax.scatter(last_x, last_y, color='red', zorder=5, s=20)
        ax.text(last_x + 2, last_y,
                f'Last: {last_y:.2f}',
                fontsize=10,
                color='darkred',
                bbox=dict(facecolor='white', edgecolor='gray', alpha=0.8))
    
    plt.tight_layout()
    
    # Refresh plot
    fig.canvas.draw()
    fig.canvas.flush_events()

# Schedule updates every minute
schedule.every(1).minutes.do(update_chart)

# Initial run
update_chart()

# Main execution loop
try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print("Program stopped by user")
    plt.ioff()
    plt.close(fig)
    sys.exit(0)