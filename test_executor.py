"""
Testes unitários para o módulo executor.py.
"""
import sys
import pytest

# Garantir mock do MetaTrader5
if 'MetaTrader5' in sys.modules:
    mock_mt5 = sys.modules['MetaTrader5']
else:
    class MockMT5Module:
        TRADE_ACTION_PENDING = 5
        TRADE_ACTION_REMOVE = 6
        TRADE_ACTION_DEAL = 1
        TRADE_RETCODE_DONE = 10009
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TYPE_BUY_STOP = 4
        ORDER_TYPE_SELL_STOP = 5
        ORDER_FILLING_RETURN = 2
        ORDER_FILLING_FOK = 0
        ORDER_FILLING_IOC = 1
        POSITION_TYPE_BUY = 0
        POSITION_TYPE_SELL = 1
        SYMBOL_FILLING_FOK = 1
        SYMBOL_FILLING_IOC = 2

        _mock_positions = []
        _mock_orders = []

        def initialize(self): return True
        def shutdown(self): pass
        def symbol_info(self, symbol):
            return type('obj', (object,), {
                'digits': 5, 'point': 0.00001, 'trade_tick_size': 0.00001,
                'volume_step': 0.01, 'volume_min': 0.01, 'volume_max': 100.0,
                'filling_mode': 2, 'visible': True, 'trade_mode': 1
            })()
        def symbol_select(self, symbol, enable): return True
        def order_send(self, request):
            return type('obj', (object,), {'retcode': 10009, 'order': 12345, 'comment': 'Success'})()
        def positions_get(self, ticket=None, symbol=None):
            return self._mock_positions
        def orders_get(self, symbol=None):
            return self._mock_orders or []
        def symbol_info_tick(self, symbol):
            return type('obj', (object,), {'bid': 1.12345, 'ask': 1.12350})()

    mock_mt5 = MockMT5Module()
    sys.modules['MetaTrader5'] = mock_mt5

import executor


def test_format_price():
    sym_info = type('obj', (object,), {'digits': 5, 'point': 0.00001, 'trade_tick_size': 0.00001})()
    formatted = executor._format_price(1.1234567, sym_info)
    assert formatted == 1.12346

    sym_info_zero_tick = type('obj', (object,), {'digits': 2, 'point': 0.01, 'trade_tick_size': 0.0})()
    formatted_zero = executor._format_price(100.567, sym_info_zero_tick)
    assert formatted_zero == 100.57

    assert executor._format_price(10.5, None) == 10.5


def test_normalize_volume():
    sym_info = type('obj', (object,), {'volume_step': 0.01, 'volume_min': 0.01, 'volume_max': 10.0})()
    assert executor._normalize_volume(0.015, sym_info) == 0.01
    assert executor._normalize_volume(0.005, sym_info) == 0.01  # clamped to min
    assert executor._normalize_volume(15.0, sym_info) == 10.0   # clamped to max

    sym_info_invalid_step = type('obj', (object,), {'volume_step': 0.0, 'volume_min': 0.01, 'volume_max': 10.0})()
    assert executor._normalize_volume(0.025, sym_info_invalid_step) == 0.02


def test_get_filling_type():
    sym_info_fok = type('obj', (object,), {'filling_mode': mock_mt5.SYMBOL_FILLING_FOK})()
    assert executor._get_filling_type(sym_info_fok) == mock_mt5.ORDER_FILLING_FOK

    sym_info_ioc = type('obj', (object,), {'filling_mode': mock_mt5.SYMBOL_FILLING_IOC})()
    assert executor._get_filling_type(sym_info_ioc) == mock_mt5.ORDER_FILLING_IOC

    sym_info_return = type('obj', (object,), {'filling_mode': 0})()
    assert executor._get_filling_type(sym_info_return) == mock_mt5.ORDER_FILLING_RETURN


def test_get_symbol_info():
    info = executor.get_symbol_info("EURUSD")
    assert info is not None
    assert info.digits == 5


def test_get_tick_size():
    sym_info = type('obj', (object,), {'trade_tick_size': 0.0001, 'point': 0.00001})()
    assert executor.get_tick_size(sym_info) == 0.0001

    sym_info_zero = type('obj', (object,), {'trade_tick_size': 0.0, 'point': 0.00001})()
    assert executor.get_tick_size(sym_info_zero) == 0.00001
