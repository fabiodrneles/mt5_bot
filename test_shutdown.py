"""
Testes para comportamento de shutdown do bot.
Usam mock do MetaTrader5 e mocks dos metodos do `executor` para verificar ações.
"""
import sys
import time


# Recriar mock do MetaTrader5 (leve) para isolar testes
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



# Use existing MetaTrader5 mock if present (to avoid clobbering other tests),
# otherwise install our mock for isolated runs.
if 'MetaTrader5' in sys.modules:
    mock_mt5 = sys.modules['MetaTrader5']
else:
    mock_mt5 = MockMT5Module()
    sys.modules['MetaTrader5'] = mock_mt5

import config
import logger
import executor
import main
import persistence

logger.setup_logger()


def test_shutdown_save_only_does_not_cancel(monkeypatch):
    """A acao save-only nao deve chamar cancel_order."""
    config.SYMBOLS = ['TESTSYM']

    cancelled = []

    def fake_cancel(ticket):
        cancelled.append(ticket)

    # For save-only we ensure there is an order present but cancel shouldn't be called
    def fake_get_orders(symbol):
        return [type('o', (), {'ticket': 1, 'magic': config.MAGIC})()]

    monkeypatch.setattr(executor, 'get_current_orders', fake_get_orders)
    monkeypatch.setattr(executor, 'cancel_order', fake_cancel)
    monkeypatch.setattr(persistence, 'save_states', lambda x: None)
    monkeypatch.setattr(persistence, 'load_states', lambda: None)

    # Force immediate shutdown path
    main._shutdown_action = 'save-only'
    main._shutdown_requested = True

    main.run_bot()

    assert cancelled == [], "Nenhuma ordem deveria ter sido cancelada no save-only"


def test_shutdown_cancel_open_calls_cancel(monkeypatch):
    """A acao cancel-open deve chamar cancel_order para ordens retornadas."""
    config.SYMBOLS = ['TESTSYM']

    cancelled = []

    def fake_cancel(ticket):
        cancelled.append(ticket)

    def fake_get_orders(symbol):
        return [type('o', (), {'ticket': 99, 'magic': config.MAGIC})()]

    monkeypatch.setattr(executor, 'get_current_orders', fake_get_orders)
    monkeypatch.setattr(executor, 'cancel_order', fake_cancel)
    monkeypatch.setattr(persistence, 'save_states', lambda x: None)
    monkeypatch.setattr(persistence, 'load_states', lambda: None)

    main._shutdown_action = 'cancel-open'
    main._shutdown_requested = True

    main.run_bot()

    assert 99 in cancelled, "A ordem retornada deveria ter sido cancelada"


def test_shutdown_wait_flat_when_already_flat(monkeypatch):
    """Se ja estiver sem posicoes/ordens, wait-flat nao bloqueia e finaliza normalmente."""
    config.SYMBOLS = ['TESTSYM']

    # Sem posicoes nem ordens
    monkeypatch.setattr(executor, 'get_current_positions', lambda s: [])
    monkeypatch.setattr(executor, 'get_current_orders', lambda s: [])

    called = {'saved': False}
    def fake_save(states):
        called['saved'] = True

    monkeypatch.setattr(persistence, 'save_states', fake_save)
    monkeypatch.setattr(persistence, 'load_states', lambda: None)

    main._shutdown_action = 'wait-flat'
    main._shutdown_requested = True

    main.run_bot()

    assert called['saved'], "save_states deve ter sido chamado durante shutdown"
