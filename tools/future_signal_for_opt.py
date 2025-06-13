from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
import pandas as pd
from datetime import datetime, timedelta
import time

xtdc.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdc.init()

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

today = datetime.now().date().strftime("%Y%m%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
n = 0.08  # 交易价格的涨跌幅度

# xtdata.get_full_tick(code_list)

with open("./data/code.txt", "r") as f:
    codes = f.read().splitlines()


def get_market_data(
    codes: list, period: str, start_time: str, end_time: str, count: int
) -> dict:
    for code in codes:
        xtdata.subscribe_quote(code, period, start_time, end_time, count, callback=None)
        xtdata.download_history_data(code, period, start_time, end_time)

    market_data = xtdata.get_market_data_ex(
        [],
        codes,
        period,
        start_time,
        end_time,
        count=count,
        dividend_type="none",
        fill_data=False,
    )

    for code in codes:
        if market_data[code].empty:
            print(f"数据 {code} 获取失败！")
            break
    return market_data


print(get_market_data(["30888.SH"], "1d", "20240610", yesterday, -1))

main_contract = []
for code in codes:
    data = xtdata.get_main_contract(code)
    if data:  # type: ignore
        main_contract.append(data)
        # print(f"Main contract for {code}: {data}")
    else:
        print(f"No main contract found for {code}")
# main_contract = 'ag2508.SF'

# 获取所有主力合约的历史数据,以dict形式存放
dict_data = get_market_data(main_contract, "1d", "20240610", yesterday, -1)

returns_dict = {}
for contract, df in dict_data.items():
    # 只取close列，计算日收益率
    returns_dict[contract] = df["close"].pct_change()

# 2. 合并为一个DataFrame，index为日期，columns为合约
returns_df = pd.DataFrame(returns_dict)

# 3. 计算相关系数矩阵
corr_matrix = returns_df.corr()

corr_matrix = corr_matrix.fillna(0)  # 填充NaN值为0
corr_matrix = corr_matrix.round(2)  # 保留两位小数
corr_matrix = corr_matrix[corr_matrix != 1]  # 去除对角线元素

# 保存结果到字典
corr_top_bottom = {}

for contract in corr_matrix.columns:
    sorted_corr = (
        corr_matrix[contract]
        .drop(labels=[contract], errors="ignore")
        .sort_values(ascending=False)
    )
    top10 = sorted_corr.head(10).to_dict()
    bottom10 = sorted_corr.tail(10).to_dict()
    corr_top_bottom[contract] = {"top10": top10, "bottom10": bottom10}


# rows = []
# for contract, v in corr_top_bottom.items():
#     for idx, value in v["top10"].items():
#         rows.append({"contract": contract, "type": "top", "target": idx, "corr": value})
#     for idx, value in v["bottom10"].items():
#         rows.append(
#             {"contract": contract, "type": "bottom", "target": idx, "corr": value}
#         )

# df_corr = pd.DataFrame(rows)
# df_corr.to_csv("contract_corr_top_bottom.csv", index=False, encoding="utf-8-sig")

# print(df_corr)
# # 如需只看某个合约的结果，可用：
# print(df_corr[df_corr["contract"] == "ag2508.SF"])

dict_history = {}
# data = xtdata.get_full_tick(codes)

for contract in main_contract:
    close_min = dict_data[contract]["close"].min()
    close_max = dict_data[contract]["close"].max()
    dict_history[contract] = {"close_min": close_min, "close_max": close_max}

#
# df = xtdata.get_market_data_ex(field_list=[], stock_list=[main_contract], period='1m',
#                                         start_time=today, end_time=today, count=-1)
# df = xtdata.get_market_data_ex(field_list=[], stock_list=[main_contract], period='1d',
#                                         start_time='20250501', end_time=today, count=-20)
# close_min = df[main_contract]['close'].min()
# close_max = df[main_contract]['close'].max()


columns = ["signal", "pos", "neg", "strike", "min", "max", "price"]
df_results = pd.DataFrame(index=main_contract, columns=columns)
df_results["pos"] = 0
df_results["neg"] = 0


def init_signal_stats(main_contract, dict_history, start, today):
    """
    用今日历史数据初始化每个合约的pos/neg统计
    """
    stats = {}
    # 获取1分钟历史数据
    hist_data = get_market_data(main_contract, "1m", start, today, -1)
    for contract in main_contract:
        close_min = dict_history[contract]["close_min"]
        close_max = dict_history[contract]["close_max"]
        closes = hist_data[contract]["close"]
        pos = (closes > close_max).sum()
        neg = (closes < close_min).sum()
        stats[contract] = {"pos": int(pos), "neg": int(neg)}
    return stats


def count_breakouts(closes, window_size=5, min_days=18, max_days=22):
    """
    统计最近max_days天内，每个window_size天窗口内创新高/低的次数
    返回：high_count, low_count
    """
    closes = closes[-max_days:]
    high_count = 0
    low_count = 0
    for i in range(max_days - window_size + 1):
        window = closes[i : i + window_size]
        if window[-1] == max(window):
            high_count += 1
        if window[-1] == min(window):
            low_count += 1
    return high_count, low_count


def update_signal(df_results, contract, closes, close_now, close_min, close_max, n):
    """
    用当前数据和18-22天close序列统计信号和strike
    """
    count_pos = df_results.at[contract, "pos"]
    count_neg = df_results.at[contract, "neg"]

    # 原有逻辑
    if close_now > close_max:
        count_pos += 1
        df_results.at[contract, "pos"] = count_pos
    elif close_now < close_min:
        count_neg += 1
        df_results.at[contract, "neg"] = count_neg

    if count_neg > count_pos:
        df_results.at[contract, "strike"] = close_now * (1 + n)
    elif count_pos > count_neg:
        df_results.at[contract, "strike"] = close_now * (1 - n)

    # 新增：统计18-22天内5天窗口创新高/低次数
    high_count, low_count = count_breakouts(
        list(closes), window_size=5, min_days=18, max_days=22
    )

    # 你可以自定义信号阈值
    if high_count >= 10:
        df_results.at[contract, "signal"] = 2
        print(f"18-22天内5天窗口创新高次数{high_count}，{contract}发出突破高点信号")
    elif low_count >= 10:
        df_results.at[contract, "signal"] = -2
        print(f"18-22天内5天窗口创新低次数{low_count}，{contract}发出突破低点信号")
    # 保留原有信号
    elif count_pos >= 30:
        df_results.at[contract, "signal"] = 1
        print(
            f"Sell Put信号: {contract} at price {df_results.at[contract, 'strike']}，现在价格: {close_now}， 最高价: {close_max}"
        )
    elif count_neg >= 30:
        df_results.at[contract, "signal"] = -1
        print(
            f"Sell Call信号: {contract} at price {df_results.at[contract, 'strike']}，现在价格: {close_now}， 最低价: {close_min}"
        )


morning_start = datetime.now().strftime("%Y%m%d") + "090000"

signal_stats = init_signal_stats(main_contract, dict_history, morning_start, today)

columns = ["signal", "pos", "neg", "strike", "min", "max", "price"]
df_results = pd.DataFrame(index=main_contract, columns=columns)
df_results["pos"] = [signal_stats[c]["pos"] for c in main_contract]
df_results["neg"] = [signal_stats[c]["neg"] for c in main_contract]


while True:
    current_time = datetime.now().time()
    morning_start = datetime.strptime("09:00:00", "%H:%M:%S").time()
    morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
    afternoon_start = datetime.strptime("13:30:00", "%H:%M:%S").time()
    afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()
    print(f"当前时间: {current_time}")
    if current_time > afternoon_start and current_time < afternoon_end:
        minutes_open = (
            datetime.combine(datetime.today(), current_time)
            - datetime.combine(datetime.today(), afternoon_start)
        ).seconds // 60
        print(f"已经是下午时间: {current_time}，已开市{minutes_open}分钟")
    elif (
        current_time > datetime.strptime("09:00:00", "%H:%M:%S").time()
        and current_time < datetime.strptime("11:30:00", "%H:%M:%S").time()
    ):
        minutes_open = (
            datetime.combine(datetime.today(), current_time)
            - datetime.combine(datetime.today(), morning_start)
        ).seconds // 60
        print(f"已经是上午时间: {current_time}，已开市{minutes_open}分钟")

    df = get_market_data(main_contract, "1m", today, today, 1)

    for contract in main_contract:
        close_min = dict_history[contract]["close_min"]
        close_max = dict_history[contract]["close_max"]
        close_now = df[contract]["close"].iloc[-1]
        closes = list(dict_data[contract]["close"])  # 传入全部close序列

        df_results.at[contract, "min"] = close_min
        df_results.at[contract, "max"] = close_max
        df_results.at[contract, "price"] = close_now
        update_signal(df_results, contract, closes, close_now, close_min, close_max, n)
    df_sorted = df_results.sort_values(
        by=["signal", "pos", "neg", "strike"], ascending=[False, False, False, False]
    )
    print(df_sorted)
    time.sleep(59)
