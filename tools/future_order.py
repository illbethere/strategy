# coding:GBK
import datetime
import time
import warnings
from typing import Union

from xtquant import xtdata, xttrader
from xtquant.qmttools.contextinfo import ContextInfo
from xtquant.qmttools.functions import get_trade_detail_data, passorder
from xtquant.xttype import StockAccount


def get_future_positions(xt_trader, account):
    """
    获取期货持仓信息
    :param xt_trader: XtQuantTrader实例
    :param account: 账户信息(StockAccount对象)
    :return: 持仓字典 {合约代码: {'direction': 方向, 'volume': 手数, 'frozen': 冻结手数}}
    """
    positions = {}

    # 查询所有持仓
    position_list = xt_trader.query_stock_positions(account)

    for position in position_list:
        if position.exchange_id in ['CFE', 'SHF', 'DCE', 'CZC', 'INE']:  # 期货交易所代码
            contract_code = "{position.stock_code}.{position.exchange_id}"
            positions[contract_code] = {
                'direction': 'long' if position.position_direction == 1 else 'short',
                'volume': position.volume,
                'frozen': position.frozen_volume,
                'market_value': position.market_value,
                'cost_price': position.cost_price
            }

    return positions


def order_target_volume(future_code: str, target_volume: int, account: StockAccount,
                        contextinfo: ContextInfo, xt_trader: xttrader.XtQuantTrader,
                        order_id: str = '', price=-1, quote_mode: str = 'backtest'):
    """
    期货目标手数调整函数(修正版)
    """
    if quote_mode in ['realtime', 'all']:
        # 获取当前持仓
        positions = get_future_positions(xt_trader, account)
        current_pos = positions.get(future_code, {'direction': None, 'volume': 0})

        # 计算需要调整的量
        if target_volume >= 0:  # 目标为多头
            if current_pos['direction'] == 'short':
                # 先平空头
                close_volume = min(current_pos['volume'], abs(target_volume))
                order_future(xt_trader, account, future_code, 34, close_volume, price, order_id)

            # 开多头
            open_volume = target_volume - (current_pos['volume'] if current_pos['direction'] == 'long' else 0)
            if open_volume > 0:
                order_future(xt_trader, account, future_code, 23, open_volume, price, order_id)

        else:  # 目标为空头
            if current_pos['direction'] == 'long':
                # 先平多头
                close_volume = min(current_pos['volume'], abs(target_volume))
                order_future(xt_trader, account, future_code, 33, close_volume, price, order_id)

            # 开空头
            open_volume = abs(target_volume) - (current_pos['volume'] if current_pos['direction'] == 'short' else 0)
            if open_volume > 0:
                order_future(xt_trader, account, future_code, 24, open_volume, price, order_id)


def order_future(xt_trader, account, future_code, order_type, volume, price, order_id):
    """
    期货下单辅助函数
    :param order_type: 23-开多 24-开空 33-平多 34-平空
    """
    remark = datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
    xt_trader.order_stock_async(
        account, future_code, order_type,
        volume, 5 if price == -1 else 11, price,
        'future_order', remark
    )


def order_target_margin(future_code: str, target_margin: float, account: Union[str, StockAccount],
                        contextinfo: ContextInfo, order_id: str = '', price=-1,
                        xt_trader: Union[None, xttrader.XtQuantTrader] = None,
                        quote_mode: str = 'backtest', quick_trade=True) -> None:
    """
    按照保证金规模调整持仓
    :param target_margin: 目标保证金，正数表示多头，负数表示空头
    """
    if quote_mode in ['realtime', 'all']:
        if not isinstance(account, StockAccount):
            raise TypeError("实盘/模拟盘传入账户应当为StockAccount类型")
        if not isinstance(xt_trader, xttrader.XtQuantTrader):
            raise TypeError("实盘/模拟盘应当传入xt_trader参数，且类型为XtQuantTrader")

        # 获取合约乘数和保证金比例
        contract_info = xtdata.get_instrument_detail(future_code)
        contract_multiplier = contract_info['contract_multiplier']  # 合约乘数
        margin_ratio = contract_info['long_margin_ratio']  # 保证金比例

        # 获取最新价格
        last_price = xtdata.get_full_tick([future_code])[future_code]['lastPrice']

        # 计算目标手数
        if target_margin >= 0:  # 多头
            target_volume = int(target_margin / (last_price * contract_multiplier * margin_ratio))
        else:  # 空头
            target_volume = -int(abs(target_margin) / (last_price * contract_multiplier * margin_ratio))

        # 调用按手数调整的函数
        order_target_volume(future_code, target_volume, account, contextinfo,
                            order_id, price, xt_trader, quote_mode, quick_trade)
    else:
        # 回测模式类似处理
        pass