# -*- coding: utf-8 -*-
# 数据读写于“./data/”目录下
from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
import pandas as pd
from datetime import datetime

xtdc.set_token("4065054877ce5724155dbc5bcba200381ce5eb35")
xtdc.init()


class G:
    def __init__(self):
        self.today = ""
        self.path = "./data/"


g = G()
g.today = str(datetime.today().strftime("%Y%m%d"))


def get_market_data(
    codes: list, period: str, start_time: str, end_time: str, count: int
) -> dict:
    """获取市场数据"""
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


def read_contract_deal():
    date = g.today[-6:]
    try:
        # read_path = g.path + f"成交记录_{date}.csv"
        read_path = g.path + f"成交记录_250611.csv"
        df = pd.read_csv(read_path, encoding="gbk")
        return df
    except Exception as e:
        print(e)


def save_contract_deal(df):
    save_path = g.path + f"contract_deal_{g.today}.csv"
    if not isinstance(df, pd.DataFrame):
        print("传入的参数不是DataFrame类型")
        return
    df.to_csv(
        save_path,
        index=False,
        mode="w",
        encoding="utf-8-sig",
    )
    print(f"合约成交数据已保存到 {save_path}")


def daily_report_contract_deal():
    df = read_contract_deal()
    output_df = df.copy()
    output_df = output_df.reset_index(drop=True)

    def get_market_name(name):
        if name == "上期所":
            return "SF"
        elif name == "大商所":
            return "DF"
        elif name == "郑商所":
            return "ZF"
        elif name == "中金所":
            return "CF"
        elif name == "广交所":
            return "GF"
        elif name == "上海国际能源交易中心":
            return "INE"
        else:
            print(f"未知市场名称: {name}")
            return "UNKNOWN"

    def get_multiplier(name):
        try:
            detail = xtdata.get_option_detail_data(name)
            if detail is not None:
                return detail.get("VolumeMultiple", None)
            else:
                print(f"{name} 获取option detail数据失败: 返回None")
                return None
        except Exception as e:
            print(f"{name} 获取VolumeMultiple失败: {e}")
            return None

    def get_object_price(name, time):
        today = g.today
        time = str(time)
        try:
            option_detail = xtdata.get_option_detail_data(name)
            object_code = (
                option_detail["OptUndlCode"] + "." + option_detail["OptUndlMarket"]
            )
            data = get_market_data([object_code], "tick", "20250604", today, -1)[
                object_code
            ]
            value = data.loc[time, "lastClose"]
            return value
        except Exception as e:
            print(e)
            return 0

    output_df["交易所"] = output_df["交易所"].apply(get_market_name)
    output_df["position"] = output_df["成交手数"].astype(int)
    output_df["price"] = output_df["成交价格"].astype(float)
    output_df["name"] = output_df["合约"] + "." + output_df["交易所"]
    output_df["multiplier"] = output_df["name"].apply(get_multiplier)
    output_df["trade_fee"] = output_df["手续费"].astype(float)
    # output_df["time"] = pd.to_datetime(
    #     g.today + " " + output_df["成交时间"], format="%Y%m%d %H:%M:%S"
    # ).dt.strftime("%Y%m%d%H%M%S")
    output_df["time"] = pd.to_datetime(
        "20250611" + " " + output_df["成交时间"], format="%Y%m%d %H:%M:%S"
    ).dt.strftime("%Y%m%d%H%M%S")
    output_df["object_price"] = output_df.apply(
        lambda row: get_object_price(row["name"], row["time"]), axis=1
    )
    output_df = output_df[
        ["name", "time", "position", "price", "trade_fee", "multiplier", "object_price"]
    ]
    return output_df


if __name__ == "__main__":
    report = daily_report_contract_deal()
    # save_contract_deal(report)
    print("合约成交数据处理完成！")
    print(report)
