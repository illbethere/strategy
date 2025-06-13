from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
from datetime import datetime, timedelta
import time
xtdc.set_token('4065054877ce5724155dbc5bcba200381ce5eb35')
xtdc.init()

today = datetime.now().date().strftime('%Y%m%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')


# xtdata.get_full_tick(code_list)

with open('data/code.txt', 'r') as f:
    codes = f.read().splitlines()

main_contract = []
for code in codes:
    data = xtdata.get_main_contract(code)
    if data:
        main_contract.append(data)
    #     print(f"Main contract for {code}: {data}")
    # else:
    #     print(f"No main contract found for {code}")
# main_contract = 'ag2508.SF'
dict_history = {}
# data = xtdata.get_full_tick(codes)
for contract in main_contract:
    xtdata.subscribe_quote(contract, period='1d', start_time = '20250501', end_time = yesterday, count=20)
# df = xtdata.get_market_data_ex(field_list=[], stock_list=[main_contract], period='1m', 
#                                         start_time=today, end_time=today, count=-1)
    df = xtdata.get_market_data_ex(field_list=['close'], stock_list=[contract], period='1d', 
                                            start_time='20250501', end_time=yesterday, count=20)
    
    close_min = df[contract]['close'].min() 
    close_max = df[contract]['close'].max()
    dict_history[contract] = {'close_min': close_min, 'close_max': close_max}

# 
# df = xtdata.get_market_data_ex(field_list=[], stock_list=[main_contract], period='1m', 
#                                         start_time=today, end_time=today, count=-1)
# df = xtdata.get_market_data_ex(field_list=[], stock_list=[main_contract], period='1d', 
#                                         start_time='20250501', end_time=today, count=-20)
# close_min = df[main_contract]['close'].min() 
# close_max = df[main_contract]['close'].max()

while True:
    current_time = datetime.now()
    nowaday = datetime.now().date()
    specific_time = datetime.combine(nowaday, datetime.min.time()) + timedelta(hours=15)
    print(f'现在是 {current_time}')
    if  current_time >= specific_time:
        break
    count_dict = {}
    for contract in main_contract:
        close_min = dict_history[contract]['close_min']
        close_max = dict_history[contract]['close_max']
        xtdata.subscribe_quote(contract, period='1m', start_time = '20250601', end_time = today, count=1)
        df = xtdata.get_market_data_ex(field_list=['close'], stock_list=[contract], period='1m', 
                                            start_time='20250601', end_time=today, count=1)
        close_now = df[contract]['close'].iloc[-1]
        if contract not in count_dict:
            count_dict[contract] = {'count_pos': 0, 'count_neg': 0}
            count_pos = 0
            count_neg = 0
        else:
            count_pos = count_dict[contract]['count_pos']
            count_neg = count_dict[contract]['count_neg']
        
        if close_now.size != 0:
            if close_now > close_max :
                count_dict[contract]['count_pos'] += 1
                count_pos = count_dict[contract]['count_pos']
            elif close_now < close_min:
                count_dict[contract]['count_neg'] += 1
                count_neg = count_dict[contract]['count_neg']
            count_dict[contract] = {'count_pos': count_pos, 'count_neg': count_neg}
            
            if count_pos >= 1:
                print(f"{contract}信号为1,卖看跌期权, 历史最高位{close_max}，现价位{close_now}")
            elif count_neg >= 1:
                print(f"{contract}信号为-1,卖看涨期权, 历史最低位{close_min}，现价位{close_now}")
    print('循环中。。。')
    time.sleep(60)

