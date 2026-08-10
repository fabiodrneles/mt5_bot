# Pytest conftest to ensure a consistent MetaTrader5 mock available for all tests
import sys

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
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    TIMEFRAME_H4 = 16388
    TIMEFRAME_D1 = 16392
    SYMBOL_TRADE_MODE_DISABLED = 0
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
        if self._mock_positions:
            if ticket:
                return [p for p in self._mock_positions if p.ticket == ticket] or None
            return self._mock_positions
        return []
    def orders_get(self, symbol=None):
        return self._mock_orders or []
    def symbol_info_tick(self, symbol):
        return type('obj', (object,), {'bid': 1.12345, 'ask': 1.12350})()
    def copy_rates_from_pos(self, symbol, tf, start, count):
        return []
    def last_error(self):
        return (0, 'OK')
    def account_info(self):
        return type('obj', (object,), {'login': 123, 'name': 'Test', 'balance': 1000.0, 'currency': 'USD'})()

# Install into sys.modules if not present
if 'MetaTrader5' not in sys.modules:
    sys.modules['MetaTrader5'] = MockMT5Module()

import pytest
import tracker
import risk_calculator

@pytest.fixture(autouse=True)
def isolate_trades(tmp_path, monkeypatch):
    test_trades_file = tmp_path / "test_trades.json"
    monkeypatch.setattr(tracker, "_TRADES_FILE", str(test_trades_file))
    monkeypatch.setattr(risk_calculator, "is_within_trading_hours", lambda *args, **kwargs: True)


