from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
import re
xtdc.set_token('4065054877ce5724155dbc5bcba200381ce5eb35')
xtdc.init()

market = 'DF'
data = xtdata.get_stock_list_in_sector(market)
codes = []
for code in data:
    if len(code) == 7 and 'JQ00' not in code and '00' in code:
        codes.append(code)
print(codes)

main_contract = []
for code in codes:
    data = xtdata.get_main_contract(code)
    if data: # type: ignore
        main_contract.append(data)
        # print(f"Main contract for {code}: {data}")
    else:
        print(f"No main contract found for {code}")


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


option_codes = get_option_code(xtdata, market, 2)

for code in main_contract:
    print(code)
    print(xtdata.get_option_undl_data(code))

# for i in main_contract:
#     i = i.replace('.SF', '')
#     for j in option_codes:
#         if i in j:
#             print(j)
#             with open('./data/code_opt.txt', 'a', encoding='utf-8') as f:
#                 f.write(j + '\n')

# print(main_contract)

# with open('./data/code.txt', 'ab') as f: # wb mode in first time then ab
#     for code in codes:
#         f.write(code.encode('utf-8') + b'\n')
