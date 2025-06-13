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
    ��ȡ�ڻ��ֲ���Ϣ
    :param xt_trader: XtQuantTraderʵ��
    :param account: �˻���Ϣ(StockAccount����)
    :return: �ֲ��ֵ� {��Լ����: {'direction': ����, 'volume': ����, 'frozen': ��������}}
    """
    positions = {}

    # ��ѯ���гֲ�
    position_list = xt_trader.query_stock_positions(account)

    for position in position_list:
        if position.exchange_id in ['CFE', 'SHF', 'DCE', 'CZC', 'INE']:  # �ڻ�����������
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
    �ڻ�Ŀ��������������(������)
    """
    if quote_mode in ['realtime', 'all']:
        # ��ȡ��ǰ�ֲ�
        positions = get_future_positions(xt_trader, account)
        current_pos = positions.get(future_code, {'direction': None, 'volume': 0})

        # ������Ҫ��������
        if target_volume >= 0:  # Ŀ��Ϊ��ͷ
            if current_pos['direction'] == 'short':
                # ��ƽ��ͷ
                close_volume = min(current_pos['volume'], abs(target_volume))
                order_future(xt_trader, account, future_code, 34, close_volume, price, order_id)

            # ����ͷ
            open_volume = target_volume - (current_pos['volume'] if current_pos['direction'] == 'long' else 0)
            if open_volume > 0:
                order_future(xt_trader, account, future_code, 23, open_volume, price, order_id)

        else:  # Ŀ��Ϊ��ͷ
            if current_pos['direction'] == 'long':
                # ��ƽ��ͷ
                close_volume = min(current_pos['volume'], abs(target_volume))
                order_future(xt_trader, account, future_code, 33, close_volume, price, order_id)

            # ����ͷ
            open_volume = abs(target_volume) - (current_pos['volume'] if current_pos['direction'] == 'short' else 0)
            if open_volume > 0:
                order_future(xt_trader, account, future_code, 24, open_volume, price, order_id)


def order_future(xt_trader, account, future_code, order_type, volume, price, order_id):
    """
    �ڻ��µ���������
    :param order_type: 23-���� 24-���� 33-ƽ�� 34-ƽ��
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
    ���ձ�֤���ģ�����ֲ�
    :param target_margin: Ŀ�걣֤��������ʾ��ͷ��������ʾ��ͷ
    """
    if quote_mode in ['realtime', 'all']:
        if not isinstance(account, StockAccount):
            raise TypeError("ʵ��/ģ���̴����˻�Ӧ��ΪStockAccount����")
        if not isinstance(xt_trader, xttrader.XtQuantTrader):
            raise TypeError("ʵ��/ģ����Ӧ������xt_trader������������ΪXtQuantTrader")

        # ��ȡ��Լ�����ͱ�֤�����
        contract_info = xtdata.get_instrument_detail(future_code)
        contract_multiplier = contract_info['contract_multiplier']  # ��Լ����
        margin_ratio = contract_info['long_margin_ratio']  # ��֤�����

        # ��ȡ���¼۸�
        last_price = xtdata.get_full_tick([future_code])[future_code]['lastPrice']

        # ����Ŀ������
        if target_margin >= 0:  # ��ͷ
            target_volume = int(target_margin / (last_price * contract_multiplier * margin_ratio))
        else:  # ��ͷ
            target_volume = -int(abs(target_margin) / (last_price * contract_multiplier * margin_ratio))

        # ���ð����������ĺ���
        order_target_volume(future_code, target_volume, account, contextinfo,
                            order_id, price, xt_trader, quote_mode, quick_trade)
    else:
        # �ز�ģʽ���ƴ���
        pass