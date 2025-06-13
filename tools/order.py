# coding:GBK
import datetime
import time
import warnings
from typing import Union

from xtquant import xtdata, xttrader
from xtquant.qmttools.contextinfo import ContextInfo
from xtquant.qmttools.functions import get_trade_detail_data, passorder
from xtquant.xttype import StockAccount


def order_target_value(stock_code: str, target_value, account: Union[str, StockAccount], contextinfo: ContextInfo,
                       order_id: str = '', price=-1, xt_trader: Union[None, xttrader.XtQuantTrader] = None,
                       quote_mode: str = 'backtest', quick_trade=True) -> None:
    """
    将持仓调整至目标金额，没有该持仓会买入；金额�?0时卖出全部持仓；可指定price参数，默�?-1为市价单，只支持股票.
    """
    if quote_mode in ['realtime', 'all']:
        if type(account) is not StockAccount:
            raise TypeError("实盘/模拟盘传入账户应当为StockAccount类型")
        if type(xt_trader) is None:
            raise TypeError("实盘/模拟盘应当传入xt_trader参数，且类型为XtQuantTrader")
        remark = datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
        # 循环下单直到第十个，然后维持最后委�?
        for i in range(1, 11):
            print(f'尝试下单-{i}代码:{stock_code}等待下单')
            current_value = 0
            usable_value = 0
            current_price = xtdata.get_full_tick([stock_code])[stock_code]['lastPrice']
            position_list = xt_trader.query_stock_positions(account)
            available_cash = xt_trader.query_stock_asset(account).cash
            for position in position_list:
                if position.stock_code == stock_code and position.volume > 0:
                    current_value = position.market_value
                    # current_price = xtdata.get_full_tick([stock_code])[stock_code]['lastPrice']
                    # if current_price1 != current_price:
                    #     warnings.warn(f'{stock_code}价格有变�?')
                    usable_value = position.can_use_volume / position.volume * current_value
                    break
            adjust_value = target_value - current_value
            print(f'调整数量为{adjust_value}, 当前可用数量为{usable_value}')
            if adjust_value < 0:
                if usable_value < abs(adjust_value):
                    warnings.warn(f'{stock_code}可用数量不足，将卖出所有可用持仓�?')
                    adjust_value = -usable_value

                sell_volume = abs(adjust_value) / current_price if price == -1 else abs(adjust_value) / price
                sell_volume = int(sell_volume // 100) * 100

                resp = xt_trader.order_stock_async(account, stock_code, 24, sell_volume, 5 if price == -1 else 11,
                                                   price,
                                                   'order_target_value', remark)
            else:
                buy_volume = adjust_value / current_price if price == -1 else adjust_value / price
                buy_volume = int(buy_volume // 100) * 100
                can_buy_volume = int(
                    ((available_cash - 1000) / current_price if price == -1 else (
                                                                                         available_cash - 1000) / price)) // 100 * 100
                print(available_cash, current_price)
                if can_buy_volume == 0:
                    warnings.warn('可买数量�?0')
                    
                    return
                if buy_volume <= can_buy_volume:
                    resp = xt_trader.order_stock_async(account, stock_code, 23, buy_volume,
                                                       5 if price == -1 else 11,
                                                       price,
                                                       'order_target_value', remark)
                else:
                    warnings.warn(f'原下单数量{buy_volume}，可用资金不足，将调整下单数量为{can_buy_volume}�?')
                    resp = xt_trader.order_stock_async(account, stock_code, 23, can_buy_volume,
                                                       5 if price == -1 else 11,
                                                       price,
                                                       'order_target_value', remark)
            time.sleep(5.0)
            if not quick_trade:
                break
            if i == 10:
                print(f'{stock_code}暂未成交，维持最后委�?')
                break
            orders = [
                {'status': order.order_status, 'remark': order.order_remark, 'time': order.order_time,
                 'sysid': order.order_sysid, 'id': order.order_id}
                for order in
                xt_trader.query_stock_orders(account) if order.order_remark == remark]
            if len(orders) == 0:
                print(f'{stock_code}今日无委托任�?')
                break
            orders = sorted(orders, key=lambda x: x['time'])
            print(orders)
            latest_order = orders[-1]
            # 判断交易，如未成功则撤单
            if latest_order['status'] == 56:
                break
            else:
                resp = None
                if latest_order['sysid'] is not None:
                    resp = xt_trader.cancel_order_stock_sysid_async(account, 0 if 'SH' in stock_code else 1,
                                                                    latest_order['sysid'])
                elif latest_order['id'] is not None:
                    resp = xt_trader.cancel_order_stock_async(account, latest_order['id'])
                else:
                    print(f'{stock_code}查询不到委托，无法进行撤单重�?')
                    break
                for i in range(1, 6):
                    if resp <= 0:
                        print(f'{stock_code}撤单暂未成功_{i}')
                        time.sleep(1.5)
                    elif resp is None:
                        print(f'{stock_code}撤单暂未响应_{i}')
                        time.sleep(1.5)
                    else:
                        print(f'{stock_code}撤单成功')
                        time.sleep(1.5)
                        break
                if resp <= 0:
                    print(f'{stock_code}撤单失败, 无法进行重下，维持原委托')
                    break
                elif resp is None:
                    print(f'{stock_code}撤单无响应，无法进行重下，维持原委托')
                    break
                else:
                    print(f'{stock_code}委托价调整为市价，准备重新下�?')
                    price = -1
    else:
        if type(account) is not str:
            raise TypeError('回测传入账户应当为str类型')
        position_value = {dt.m_strInstrumentID: dt.m_dMarketValue for dt in
                          get_trade_detail_data(account, 'stock', 'position')}
        position_usable_value = {dt.m_strInstrumentID: dt.m_dLastPrice * dt.m_nCanUseVolume for dt in
                                 get_trade_detail_data(account, 'stock', 'position')}
        if stock_code[:-3] in position_value.keys():
            current_value = position_value[stock_code[:-3]]
            usable_value = position_usable_value[stock_code[:-3]]
        else:
            current_value = 0
            usable_value = 0
        trade_price = 0
        if current_value < target_value:
            trade_price = target_value - current_value
            trade_type = 'buy'

            passorder(
                23, 1102, account
                , stock_code, 5 if price == -1 else 11, price, target_value - current_value
                , 'order_target_value', 1,
                datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
                , contextinfo
            )
        else:
            if current_value - target_value < usable_value:
                trade_price = current_value - target_value
                passorder(
                    24, 1102, account
                    , stock_code, 5 if price == -1 else 11, price, current_value - target_value
                    , 'order_target_value', 1,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
                    , contextinfo
                )
            else:
                trade_price = usable_value
                passorder(
                    24, 1102, account
                    , stock_code, 5 if price == -1 else 11, price, usable_value
                    , 'order_target_value', 1,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
                    , contextinfo
                )
    return


def order_target_weight(stock_code: str, target_weight, account: Union[str, StockAccount], contextinfo: ContextInfo,
                        order_id: str = '', price=-1, xt_trader: Union[None, xttrader.XtQuantTrader] = None,
                        quote_mode: str = 'backtest', quick_trade=True) -> None:
    """
    将持仓调整至目标权重，没有该持仓会买入；权重�?0时卖出全部持仓；可指定price参数，默�?-1为市价单，只支持股票
    """
    if 1 < target_weight or target_weight < 0:
        raise ValueError("目标权重应当位于0�?1之间（闭区间�?")
    if quote_mode in ['realtime', 'all']:
        if type(account) is not StockAccount:
            raise TypeError("实盘/模拟盘传入账户应当为StockAccount类型")
        if type(xt_trader) is None:
            raise TypeError("实盘/模拟盘应当传入xt_trader参数，且类型为XtQuantTrader")
        remark = datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
        for i in range(1, 11):
            print(f'尝试下单-{i}代码:{stock_code}')
            current_value = 0
            usable_value = 0
            usable_volume = 0
            current_price = \
                xtdata.get_full_tick([stock_code])[stock_code]['lastPrice']
            total_value = xt_trader.query_stock_asset(account).total_asset
            position_list = xt_trader.query_stock_positions(account)
            available_cash = xt_trader.query_stock_asset(account).cash
            for position in position_list:
                if position.stock_code == stock_code and position.volume > 0:
                    current_value = position.volume * current_price if price == -1 else position.volume * price
                    usable_value = position.can_use_volume / position.volume * current_value
                    usable_volume = position.can_use_volume
                    break
            if abs(target_weight - current_value / total_value) < 0.001:
                return
            adjust_value = (target_weight - current_value / total_value) * total_value
            # print(adjust_value, price)
            if adjust_value < 0:
                if usable_value < abs(adjust_value):
                    warnings.warn(f'{stock_code}可用数量不足，将卖出所有可用持仓�?')
                    adjust_value = -usable_value

                sell_volume = abs(adjust_value) / current_price if price == -1 else abs(adjust_value) / price
                sell_volume = int(sell_volume // 100) * 100
                if sell_volume > usable_volume:
                    warnings.warn(f'{stock_code}可用数量不足，将卖出所有可用持仓�?')
                    sell_volume = usable_volume
                resp = xt_trader.order_stock_async(account, stock_code, 24, sell_volume, 5 if price == -1 else 11,
                                                   price,
                                                   'order_target_weight', remark)
            else:
                buy_volume = adjust_value / current_price if price == -1 else adjust_value / price
                buy_volume = int(buy_volume // 100) * 100
                can_buy_volume = int(
                    (available_cash / current_price if price == -1 else available_cash / price)) // 100 * 100
                if can_buy_volume == 0:
                    warnings.warn('可买数量�?0')
                    return
                if buy_volume <= can_buy_volume:
                    resp = xt_trader.order_stock_async(account, stock_code, 23, buy_volume,
                                                       5 if price == -1 else 11,
                                                       price,
                                                       'order_target_weight', remark)
                else:
                    warnings.warn(f'原下单数量{buy_volume}，可用资金不足，将调整下单数量为{can_buy_volume}�?')
                    resp = xt_trader.order_stock_async(account, stock_code, 23, can_buy_volume,
                                                       5 if price == -1 else 11,
                                                       price,
                                                       'order_target_weight', remark)
            if not quick_trade:
                break
            if i == 10:
                print(f'{stock_code}暂未成交，维持最后委�?')
                break
            time.sleep(1.5)
            orders = [
                {'status': order.order_status, 'remark': order.order_remark, 'time': order.order_time,
                 'sysid': order.order_sysid, 'id': order.order_id}
                for order in
                xt_trader.query_stock_orders(account) if order.order_remark == remark]
            if len(orders) == 0:
                print(f'{stock_code}今日无委托任�?')
                break
            orders = sorted(orders, key=lambda x: x['time'])
            print(orders)
            latest_order = orders[-1]
            if latest_order['status'] == 56:
                break
            else:
                resp = None
                if latest_order['sysid'] is not None:
                    resp = xt_trader.cancel_order_stock_sysid_async(account, 0 if 'SH' in stock_code else 1,
                                                                    latest_order['sysid'])
                elif latest_order['id'] is not None:
                    resp = xt_trader.cancel_order_stock_async(account, latest_order['id'])
                else:
                    print(f'{stock_code}查询不到委托，无法进行撤单重�?')
                    break
                for i in range(1, 6):
                    if resp == -1:
                        print(f'{stock_code}撤单暂未成功_{i}')
                        time.sleep(0.5)
                    elif resp is None:
                        print(f'{stock_code}撤单暂未响应_{i}')
                        time.sleep(0.5)
                    else:
                        print(f'{stock_code}撤单成功')
                        break
                if resp == -1:
                    print(f'{stock_code}撤单失败, 无法进行重下，维持原委托')
                    break
                elif resp is None:
                    print(f'{stock_code}撤单无响应，无法进行重下，维持原委托')
                    break
                else:
                    print(f'{stock_code}委托价调整为市价，准备重新下�?')
                    price = -1
    else:
        if type(account) is not str:
            raise TypeError('回测传入账户应当为str类型')
        position_value = {dt.m_strInstrumentID: dt.m_dMarketValue for dt in
                          get_trade_detail_data(account, 'stock', 'position')}
        total_value = get_trade_detail_data(account, 'stock', 'ACCOUNT')[0].m_dBalance
        if stock_code[:-3] in position_value.keys():
            current_weight = position_value[stock_code[:-3]] / total_value
        else:
            current_weight = 0
        if current_weight < target_weight:
            passorder(
                23, 1113, account
                , stock_code, 5 if price == -1 else 11, price, target_weight - current_weight
                , 'order_target_weight', 1,
                datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
                , contextinfo
            )
        else:
            passorder(
                24, 1113, account
                , stock_code, 5 if price == -1 else 11, price, current_weight - target_weight
                , 'order_target_weight', 1,
                datetime.datetime.now().strftime('%Y%m%d%H%M%S') if order_id == '' else order_id
                , contextinfo
            )
    return


def order_target_contract(future_code: str, volume: int, account: Union[str, StockAccount], contextinfo: ContextInfo,
                          order_id: str = '',
                          price=-1, xt_trader: Union[None, xttrader.XtQuantTrader] = None,
                          quote_mode: str = 'backtest', quick_trade=True):
    """
    期货操作，调整至目标合约份数，负数表示空头操作，正数表示多头操作.
    """
    if quote_mode in ['realtime', 'all']:
        if type(account) is not StockAccount: raise TypeError("实盘/模拟盘传入账户应当为StockAccount类型")
        if type(xt_trader) is None: raise TypeError("实盘/模拟盘应当传入xt_trader参数，且类型为XtQuantTrader")
        remark = datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
        for i in range(1, 11):
            print(f'尝试下单-{i}代码:{future_code}')
            position_list = xt_trader.query_positions(account, 0, 0)
            current_volume = 0
            current_direction = 0
            for position in position_list:
                if position.instrument_id == future_code.split('.')[0]:
                    current_volume = position.volume
                    current_direction = 1 if position.direction == 48 else -1
                    break
            current = current_volume * current_direction
            if current == 0: #无持�?

                resp = xt_trader.order_stock_async(account, future_code, 0 if volume > 0 else 3, abs(volume),
                                                   5 if price == -1 else 11, price, 'order_target_contract',
                                                   remark)
            elif current * volume > 0: #持仓和目标方向相�?
                if volume > 0: #做多
                    if volume - current > 0: #目标多单大于持仓多单
                        resp = xt_trader.order_stock_async(account, future_code, 0, volume - current,
                                                           5 if price == -1 else 11, price
                                                           , 'order_target_contract',
                                                           remark)
                    elif volume - current < 0: #目标多单小于持仓多单
                        resp = xt_trader.order_stock_async(account, future_code, 7, current - volume,
                                                           5 if price == -1 else 11, price,
                                                           'order_target_contract',
                                                           remark)
                elif volume < 0: #做空
                    if volume - current > 0: #目标空单小于持仓空单
                        resp = xt_trader.order_stock_async(account, future_code, 9, abs(volume - current),
                                                           5 if price == -1 else 11, price,
                                                           'order_target_contract',
                                                           remark)
                    elif volume - current < 0: #目标空单大于持仓空单
                        resp = xt_trader.order_stock_async(account, future_code, 3, abs(volume - current),
                                                           5 if price == -1 else 11, price,
                                                           'order_target_contract',
                                                           remark)
            elif current * volume <= 0: #持仓与目标方向不用（平多开�?/平空开多）
                if current < 0: #平掉持仓空单
                    resp = xt_trader.order_stock_async(account, future_code, 9, abs(current), 5 if price == -1 else 11,
                                                       price,
                                                       'order_target_contract',
                                                       remark)
                else: #平掉持仓多单
                    resp = xt_trader.order_stock_async(account, future_code, 7, abs(current), 5 if price == -1 else 11,
                                                       price,
                                                       'order_target_contract',
                                                       remark)
                if volume > 0: #开�?
                    resp = xt_trader.order_stock_async(account, future_code, 0, abs(volume), 5 if price == -1 else 11,
                                                       price,
                                                       'order_target_contract',
                                                       remark)
                elif volume < 0: #开�?
                    resp = xt_trader.order_stock_async(account, future_code, 3, abs(volume), 5 if price == -1 else 11,
                                                       price,
                                                       'order_target_contract',
                                                       remark)
            if not quick_trade:
                break
            if i == 10:
                print(f'{future_code}暂未成交，维持最后委�?')
                break
            time.sleep(0.5)
            orders = [{'status': order.order_status, 'remark': order.order_remark, 'time': order.order_time,
                       'sysid': order.order_sysid, 'id':order.order_id} for order in
                      xt_trader.query_stock_orders(account) if order.order_remark == remark]
            if len(orders) == 0:
                print(f'{future_code}今日无委托任�?')
                break
            orders = sorted(orders, key=lambda x: x['time'])
            print(orders)
            latest_order = orders[-1]
            if latest_order['status'] == 56:
                break
            else:
                resp = None
                if latest_order['sysid'] is not None:
                    resp = xt_trader.cancel_order_stock_sysid_async(account, 0, latest_order['sysid'])
                elif latest_order['id'] is not None:
                    resp = xt_trader.cancel_order_stock_async(account, latest_order['id'])
                else:
                    print(f'{future_code}查询不到委托，无法进行撤单重�?')
                    break
                for i in range(1, 6):
                    if resp <= 0:
                        print(f'{future_code}撤单暂未成功_{i}')
                        time.sleep(0.5)
                    elif resp is None:
                        print(f'{future_code}撤单暂未响应_{i}')
                        time.sleep(0.5)
                    else:
                        print(f'{future_code}撤单成功')
                        time.sleep(0.5)
                        break
                if resp <= 0:
                    print(f'{future_code}撤单失败, 无法进行重下，维持原委托')
                    break
                elif resp is None:
                    print(f'{future_code}撤单无响应，无法进行重下，维持原委托')
                    break
                else:
                    print(f'{future_code}委托价调整为市价，准备重新下�?')
                    price = -1
    else:
        if type(account) is not str: raise TypeError('回测传入账户应当为str类型')
        current_volume = {dt.m_strInstrumentID: dt.m_nVolume for dt in
                          get_trade_detail_data(account, 'future', 'position')}
        current_direction = {dt.m_strInstrumentID: 1 if dt.m_nDirection == 48 else -1 for dt in
                             get_trade_detail_data(account, 'future', 'position')}
        if future_code.split('.')[0] in current_volume.keys():
            current = current_volume[future_code.split('.')[0]] * current_direction[future_code.split('.')[0]]
            if current * volume <= 0:
                if current < 0:
                    passorder(
                        9, 1101, account
                        , future_code, 5 if price == -1 else 11, price, abs(current)
                        , 'order_target_contract', 1,
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                        , contextinfo
                    )
                else:
                    passorder(
                        7, 1101, account
                        , future_code, 5 if price == -1 else 11, price, current
                        , 'order_target_contract', 1,
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                        , contextinfo
                    )
                if volume > 0:
                    passorder(
                        0, 1101, account
                        , future_code, 5 if price == -1 else 11, price, volume
                        , 'order_target_contract', 1,
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                        , contextinfo
                    )
                elif volume < 0:
                    passorder(
                        3, 1101, account
                        , future_code, 5 if price == -1 else 11, price, abs(volume)
                        , 'order_target_contract', 1,
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                        , contextinfo
                    )
            elif current * volume > 0:
                if volume > 0:
                    if volume - current > 0:
                        passorder(
                            0, 1101, account
                            , future_code, 5 if price == -1 else 11, price, volume - current
                            , 'order_target_contract', 1,
                            datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                            , contextinfo
                        )
                    elif volume - current < 0:
                        passorder(
                            7, 1101, account
                            , future_code, 5 if price == -1 else 11, price, current - volume
                            , 'order_target_contract', 1,
                            datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                            , contextinfo
                        )
                elif volume < 0:
                    if volume - current > 0:
                        passorder(
                            9, 1101, account
                            , future_code, 5 if price == -1 else 11, price, abs(volume - current)
                            , 'order_target_contract', 1,
                            datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                            , contextinfo
                        )
                    elif volume - current < 0:
                        passorder(
                            3, 1101, account
                            , future_code, 5 if price == -1 else 11, price, abs(volume - current)
                            , 'order_target_contract', 1,
                            datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                            , contextinfo
                        )

        else:
            if volume > 0:
                passorder(
                    0, 1101, account
                    , future_code, 5 if price == -1 else 11, price, volume
                    , 'order_target_contract', 1,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                    , contextinfo
                )
            elif volume < 0:
                passorder(
                    3, 1101, account
                    , future_code, 5 if price == -1 else 11, price, abs(volume)
                    , 'order_target_contract', 1,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S委托�?') if order_id == '' else order_id
                    , contextinfo
                )
    return