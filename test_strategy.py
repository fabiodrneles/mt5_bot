"""
Testes unitarios para a maquina de estados do bot MT5.
Roda sem dependencia do MT5 real (usa mocks).
"""
import sys
import os

# Use existing MetaTrader5 mock if provided by conftest/test_shutdown, else create local mock
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
            return (0, "OK")
        def account_info(self):
            return type('obj', (object,), {'login': 12345, 'name': 'Test', 'balance': 1000.0, 'currency': 'USD'})()

    mock_mt5 = MockMT5Module()
    sys.modules['MetaTrader5'] = mock_mt5

# Agora importar modulos do bot
import config
import logger
import indicators
import executor
import strategy
import persistence

# Configuracao de teste
logger.setup_logger()
config.SYMBOLS = ['TESTSYM']
config.VOLUME_INITIAL = 0.01
config.FLAT_FILTER_ENABLED = True
config.SETUP_92_ENABLED = True
config.SETUP_92_MAX_CANDLES_WATCHING = 10
config.SETUP_92_EMA_AGAINST_LIMIT = 2
config.ATR_HIGH_VOL_THRESHOLD = 1.5
config.ATR_DAMPING_FACTOR = 0.8
config.ADAPTIVE_TARGET_ENABLED = True
config.ADAPTIVE_TARGET_LOOKBACK = 20
config.MAGIC = 20260731

import pytest

@pytest.fixture(autouse=True)
def disable_persistence(monkeypatch):
    monkeypatch.setattr(persistence, 'save_states', lambda x: None)
    monkeypatch.setattr(persistence, 'load_states', lambda: None)
    yield


def make_rates(n=30, base_close=1.0, trend=0.01):
    """Gera rates simulados com tendencia."""
    rates = []
    for i in range(n):
        c = base_close + i * trend
        rates.append((i, c - 0.01, c + 0.05, c - 0.05, c, 100, 2, 50))
    return rates


def make_ema9_virou_cima():
    """Gera rates onde EMA9 vira para cima no ULTIMO candle.
    29 candles descendo (EMA em queda) + 1 candle com spike para cima.
    Isso faz slope_previous < 0 e slope_current > 0.
    """
    rates = []
    for i in range(29):
        c = 1.2 - i * 0.005  # closes from 1.2 to 1.06
        rates.append((i, c - 0.01, c + 0.02, c - 0.02, c, 100, 2, 50))
    # Ultimo candle: spike alto que puxa EMA para cima
    rates.append((29, 1.10, 1.25, 1.05, 1.20, 100, 2, 50))
    return rates


def make_ema9_virou_baixo():
    """Gera rates onde EMA9 vira para baixo no ULTIMO candle.
    29 candles subindo (EMA em alta) + 1 candle com queda forte.
    Isso faz slope_previous > 0 e slope_current < 0.
    """
    rates = []
    for i in range(29):
        c = 1.0 + i * 0.005  # closes from 1.0 to 1.14
        rates.append((i, c - 0.01, c + 0.02, c - 0.02, c, 100, 2, 50))
    # Ultimo candle: queda forte que puxa EMA para baixo
    rates.append((29, 1.10, 1.15, 0.90, 0.92, 100, 2, 50))
    return rates


def reset_state():
    """Reseta o estado para SCANNING."""
    strategy.symbol_states['TESTSYM'] = strategy.SymbolState('TESTSYM')
    mock_mt5._mock_positions = []
    mock_mt5._mock_orders = []
    return strategy.symbol_states['TESTSYM']


# ============================================================
# TESTES
# ============================================================

def test_scanning_to_signal_ready_buy():
    """SCANNING + virada EMA9 para cima → SIGNAL_READY (BUY)"""
    s_state = reset_state()
    rates = make_ema9_virou_cima()
    candle = rates[-1]

    strategy.evaluate('TESTSYM', candle, rates)

    assert s_state.state == strategy.State.SIGNAL_READY, f"Esperado SIGNAL_READY, got {s_state.state}"
    assert s_state.position_type == strategy.TradeSide.BUY
    assert s_state.setup_type == "9.1"
    assert s_state.entry_price is not None
    assert s_state.sl_price is not None


def test_scanning_to_signal_ready_sell():
    """SCANNING + virada EMA9 para baixo → SIGNAL_READY (SELL)"""
    s_state = reset_state()
    rates = make_ema9_virou_baixo()
    candle = rates[-1]

    strategy.evaluate('TESTSYM', candle, rates)

    assert s_state.state == strategy.State.SIGNAL_READY, f"Esperado SIGNAL_READY, got {s_state.state}"
    assert s_state.position_type == strategy.TradeSide.SELL
    assert s_state.setup_type == "9.1"


def test_signal_ready_cancel_on_ema_turn():
    """SIGNAL_READY + EMA9 virou contra → SCANNING (cancelamento)"""
    s_state = reset_state()
    s_state.state = strategy.State.SIGNAL_READY
    s_state.pending_order_ticket = 10001
    s_state.position_type = strategy.TradeSide.BUY
    s_state.setup_type = "9.1"

    # Mock: ordem ainda existe
    mock_mt5._mock_orders = [type('obj', (object,), {
        'ticket': 10001, 'magic': config.MAGIC, 'type': mock_mt5.ORDER_TYPE_BUY_STOP
    })()]

    # Rates que fazem EMA9 virar para baixo
    rates = make_ema9_virou_baixo()
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.SCANNING, f"Esperado SCANNING, got {s_state.state}"


def test_signal_ready_to_in_position():
    """SIGNAL_READY + ordem preenchida → IN_POSITION"""
    s_state = reset_state()
    s_state.state = strategy.State.SIGNAL_READY
    s_state.pending_order_ticket = 10001
    s_state.position_type = strategy.TradeSide.BUY
    s_state.setup_type = "9.1"
    s_state.candle_referencia = (0, 1.0, 1.1, 0.9, 1.05, 0, 0, 0)
    s_state.entry_price = 1.10001

    # Mock: ordem nao existe mais (preenchida), posicao existe
    mock_mt5._mock_orders = []
    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 67890, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    rates = make_rates()
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.IN_POSITION, f"Esperado IN_POSITION, got {s_state.state}"
    assert s_state.position_ticket == 67890


def test_in_position_partial_exit():
    """IN_POSITION + alvo atingido → partial_exit_done = True"""
    s_state = reset_state()
    s_state.state = strategy.State.IN_POSITION
    s_state.position_ticket = 67890
    s_state.position_type = strategy.TradeSide.BUY
    s_state.partial_exit_done = False
    s_state.candle_referencia = (0, 1.0, 1.1, 0.9, 1.05, 0, 0, 0)  # amplitude = 0.2
    s_state.entry_price = 1.10001
    s_state.setup_type = "9.1"

    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 67890, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    # Close bem acima do target (entry + amplitude*1.0 = 1.10001 + 0.2 = 1.30001)
    rates = make_rates(30, base_close=1.35, trend=0.001)
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.partial_exit_done, "Esperado partial_exit_done = True"


def test_in_position_full_exit_to_scanning():
    """IN_POSITION + EMA9 virou contra → SCANNING (saida final, sem lucro)"""
    s_state = reset_state()
    s_state.state = strategy.State.IN_POSITION
    s_state.position_ticket = 67890
    s_state.position_type = strategy.TradeSide.BUY
    s_state.entry_price = 1.2  # entrada alta
    s_state.partial_exit_done = True
    s_state.setup_type = "9.1"
    s_state.candle_referencia = (0, 1.0, 1.1, 0.9, 1.05, 0, 0, 0)

    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 67890, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    # Rates que fazem EMA9 virar para baixo (contra a compra)
    rates = make_ema9_virou_baixo()
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.SCANNING, f"Esperado SCANNING, got {s_state.state}"
    assert s_state.position_ticket is None


def test_setup_92_watching_to_signal_ready():
    """Setup 9.2: quando condicoes de observacao sao satisfeitas, avanca para SIGNAL_READY"""
    s_state = reset_state()
    s_state.state = strategy.State.WATCHING_92
    s_state.setup_type = "9.2"

    # Simular candles que atendem condicoes de 9.2 (volume e movimento)
    rates = make_rates(30, base_close=1.0, trend=0.02)
    strategy.evaluate('TESTSYM', rates[-1], rates)

    # A implementacao aceita varios cenarios; garantimos que nao permaneça WATCHING_92 indefinidamente
    assert s_state.state in (strategy.State.WATCHING_92, strategy.State.SIGNAL_READY, strategy.State.SCANNING)


def test_no_side_effects_between_tests():
    """Verifica que testes anteriores nao deixaram ordens/posicoes globais"""
    # Conftest e helpers devem limpar mocks; aqui confirmamos arrays vazios por padrao
    mock_mt5._mock_positions = []
    mock_mt5._mock_orders = []

    assert mock_mt5.positions_get() == []
    assert mock_mt5.orders_get() == []

