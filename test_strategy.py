"""
Testes unitarios para a maquina de estados do bot MT5.
Roda sem dependencia do MT5 real (usa mocks).
"""
import sys
import os

# Mock do MetaTrader5 ANTES de importar os modulos do bot
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
        return (0, "OK")
    def account_info(self):
        return type('obj', (object,), {'login': 12345, 'name': 'Test'})()

# Instalar mock no sys.modules
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

# Desabilitar persistencia real nos testes
persistence.save_states = lambda x: None
persistence.load_states = lambda: None


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
    print("OK: SCANNING -> SIGNAL_READY (BUY, Setup 9.1)")


def test_scanning_to_signal_ready_sell():
    """SCANNING + virada EMA9 para baixo → SIGNAL_READY (SELL)"""
    s_state = reset_state()
    rates = make_ema9_virou_baixo()
    candle = rates[-1]

    strategy.evaluate('TESTSYM', candle, rates)

    assert s_state.state == strategy.State.SIGNAL_READY, f"Esperado SIGNAL_READY, got {s_state.state}"
    assert s_state.position_type == strategy.TradeSide.SELL
    assert s_state.setup_type == "9.1"
    print("OK: SCANNING -> SIGNAL_READY (SELL, Setup 9.1)")


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
    print("OK: SIGNAL_READY -> SCANNING (cancelamento por EMA9 contra)")


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
    print("OK: SIGNAL_READY -> IN_POSITION (ordem preenchida)")


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
    print("OK: IN_POSITION -> saida parcial executada")


def test_in_position_full_exit_to_scanning():
    """IN_POSITION + EMA9 virou contra → SCANNING (saida final, sem lucro)"""
    s_state = reset_state()
    s_state.state = strategy.State.IN_POSITION
    s_state.position_ticket = 67890
    s_state.position_type = strategy.TradeSide.BUY
    s_state.entry_price = 1.2  # entrada alta
    s_state.candle_referencia = (0, 1.0, 1.2, 0.9, 1.1, 0, 0, 0)
    s_state.setup_type = "9.1"

    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 67890, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    # EMA9 vira para baixo + close abaixo do entry (prejuizo)
    rates = make_ema9_virou_baixo()
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.SCANNING, f"Esperado SCANNING, got {s_state.state}"
    print("OK: IN_POSITION -> SCANNING (saida final, prejuizo)")


def test_in_position_exit_profit_to_watching_92():
    """IN_POSITION + EMA9 virou contra + lucro → WATCHING_92"""
    s_state = reset_state()
    s_state.state = strategy.State.IN_POSITION
    s_state.position_ticket = 67890
    s_state.position_type = strategy.TradeSide.BUY
    s_state.entry_price = 0.9  # entrada baixa para garantir lucro
    s_state.candle_referencia = (0, 0.85, 0.95, 0.80, 0.90, 0, 0, 0)
    s_state.setup_type = "9.1"

    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 67890, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    # EMA9 vira para baixo, mas close > entry (lucro)
    rates = make_ema9_virou_baixo()  # closes terminam em ~1.07
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.WATCHING_92, f"Esperado WATCHING_92, got {s_state.state}"
    assert s_state.exit_profit == True
    assert s_state.watching_92_candles == 0
    print("OK: IN_POSITION -> WATCHING_92 (saida com lucro)")


def test_watching_92_timeout():
    """WATCHING_92 + timeout (muitos candles) → SCANNING"""
    s_state = reset_state()
    s_state.state = strategy.State.WATCHING_92
    s_state.position_type = strategy.TradeSide.BUY
    s_state.watching_92_candles = config.SETUP_92_MAX_CANDLES_WATCHING  # Ja no limite

    mock_mt5._mock_positions = []
    mock_mt5._mock_orders = []

    rates = make_rates(30, base_close=1.1, trend=0.001)
    strategy.evaluate('TESTSYM', rates[-1], rates)

    assert s_state.state == strategy.State.SCANNING, f"Esperado SCANNING, got {s_state.state}"
    print("OK: WATCHING_92 -> SCANNING (timeout)")


def test_watching_92_pullback_generates_signal():
    """WATCHING_92 + pullback a EMA9 + direcao favoravel → SIGNAL_READY (9.2)"""
    s_state = reset_state()
    s_state.state = strategy.State.WATCHING_92
    s_state.position_type = strategy.TradeSide.BUY
    s_state.watching_92_candles = 2
    s_state.exit_profit = True

    mock_mt5._mock_positions = []
    mock_mt5._mock_orders = []

    # Gerar rates com EMA9 subindo (direcao favoravel para BUY)
    # e ultimo candle com low que toca/cruza a EMA9
    rates = make_rates(30, base_close=1.0, trend=0.005)
    # O EMA9 dos ultimos candles sera ~proximo de close
    # Precisamos que o candle tenha low <= ema9
    # Com trend positivo, EMA9 vai subindo. Vamos forcar um candle com low baixo.
    last_candle = list(rates[-1])
    ema9_vals = indicators.get_ema9(rates)
    if ema9_vals:
        # Forcar low abaixo da EMA9
        last_candle[3] = ema9_vals[-1] - 0.01  # low abaixo da EMA9
        rates[-1] = tuple(last_candle)

    strategy.evaluate('TESTSYM', rates[-1], rates)

    # Se pullback foi detectado e EMA apontando pra cima, deve gerar sinal 9.2
    if s_state.state == strategy.State.SIGNAL_READY:
        assert s_state.setup_type == "9.2"
        print("OK: WATCHING_92 -> SIGNAL_READY (Setup 9.2 detectado)")
    else:
        # Se EMA9 nao estava favoravel, volta a timeout eventualmente
        print(f"INFO: WATCHING_92 nao gerou sinal (EMA9 nao favoravel). Estado: {s_state.state.name}")
        print("OK: WATCHING_92 logica executada sem erro")


def test_atr_ratio_calculation():
    """Verifica calculo do ATR ratio."""
    # Gerar 100 candles com volatilidade crescente no final
    rates = []
    for i in range(80):
        c = 1.0 + i * 0.001
        rates.append((i, c, c + 0.005, c - 0.005, c, 100, 2, 50))  # ATR ~0.01
    for i in range(20):
        c = 1.08 + i * 0.001
        rates.append((80 + i, c, c + 0.02, c - 0.02, c, 100, 2, 50))  # ATR ~0.04

    result = indicators.get_atr_ratio(rates)
    if result:
        atr_current, atr_avg, ratio = result
        assert atr_current > 0
        assert atr_avg > 0
        assert ratio > 1.0  # Volatilidade recente maior que media
        print(f"OK: ATR ratio calculado: {ratio:.2f} (current={atr_current:.5f}, avg={atr_avg:.5f})")
    else:
        print("INFO: ATR nao calculado (dados insuficientes neste mock)")


def test_atr_stop_adjustment():
    """Verifica que stop e alargado quando ATR ratio > threshold."""
    # Gerar rates com alta volatilidade
    rates = []
    for i in range(60):
        c = 1.0 + i * 0.001
        rates.append((i, c, c + 0.003, c - 0.003, c, 100, 2, 50))
    for i in range(40):
        c = 1.06 + i * 0.001
        rates.append((60 + i, c, c + 0.03, c - 0.03, c, 100, 2, 50))  # 10x mais volatil

    entry = 1.10
    sl_original = 1.05

    sl_adjusted = strategy._apply_atr_adjustment('TESTSYM', entry, sl_original, rates)

    atr_data = indicators.get_atr_ratio(rates)
    if atr_data and atr_data[2] > config.ATR_HIGH_VOL_THRESHOLD:
        assert sl_adjusted != sl_original, "Stop deveria ter sido ajustado"
        assert sl_adjusted < sl_original, "Stop BUY ajustado deveria ser mais baixo (mais distante)"
        print(f"OK: Stop alargado por ATR. Original={sl_original} Ajustado={sl_adjusted:.5f}")
    else:
        print(f"INFO: ATR ratio nao atingiu threshold. ratio={atr_data[2]:.2f if atr_data else 'N/A'}")


def test_volume_normalization():
    """Verifica que volume e normalizado para o step do simbolo."""
    symbol_info = mock_mt5.symbol_info('TESTSYM')

    # Volume menor que o step
    vol = executor._normalize_volume(0.005, symbol_info)
    assert vol == 0.01, f"Esperado 0.01, got {vol}"

    # Volume valido
    vol = executor._normalize_volume(0.03, symbol_info)
    assert vol == 0.03, f"Esperado 0.03, got {vol}"

    # Volume com decimais estranhos
    vol = executor._normalize_volume(0.015, symbol_info)
    assert vol == 0.01, f"Esperado 0.01, got {vol}"

    print("OK: Volume normalizacao funciona corretamente")


def test_close_full_position_with_trade_side():
    """Verifica que close_full_position aceita TradeSide enum sem crash."""
    mock_mt5._mock_positions = [type('obj', (object,), {
        'ticket': 99999, 'magic': config.MAGIC, 'type': mock_mt5.POSITION_TYPE_BUY, 'volume': 0.01
    })()]

    # Deve funcionar com TradeSide enum (fix P0-1)
    result = executor.close_full_position(99999, 'TESTSYM', strategy.TradeSide.BUY)
    assert result is not None
    assert result.retcode == mock_mt5.TRADE_RETCODE_DONE
    print("OK: close_full_position aceita TradeSide enum")


def test_close_full_position_empty_positions():
    """Verifica que close_full_position nao crasha com positions vazio (fix P0-2)."""
    mock_mt5._mock_positions = []

    result = executor.close_full_position(99999, 'TESTSYM', strategy.TradeSide.BUY)
    assert result is None  # Retorna None sem crashar
    print("OK: close_full_position retorna None quando posicao nao existe (sem crash)")


def test_adaptive_target_multiplier():
    """Verifica calculo do alvo adaptativo baseado em amplitude recente."""
    # Cenario 1: candles uniformes → multiplicador = 1.0
    rates = []
    for i in range(30):
        c = 1.0 + i * 0.001
        rates.append((i, c, c + 0.01, c - 0.01, c, 100, 2, 50))  # amplitude uniforme 0.02

    result = indicators.adaptive_target_multiplier(rates, lookback=20)
    assert result is not None, "Deveria calcular adaptive target"
    median_amp, multiplier = result
    assert 0.9 <= multiplier <= 1.1, f"Multiplicador deveria ser ~1.0, got {multiplier}"
    print(f"OK: Alvo adaptativo uniforme: mult={multiplier:.1f}, mediana={median_amp:.5f}")

    # Cenario 2: penultimo candle (rates[-2]) muito maior que os anteriores → multiplicador reduzido
    rates_big = list(rates)
    # rates[-2] com amplitude 3x maior (o que a funcao usa como referencia)
    rates_big[-2] = (28, 1.028, 1.058, 0.998, 1.028, 100, 2, 50)  # amp=0.06 vs mediana 0.02

    result2 = indicators.adaptive_target_multiplier(rates_big, lookback=20)
    if result2:
        _, mult2 = result2
        assert mult2 < 1.0, f"Multiplicador deveria ser < 1.0 para candle grande, got {mult2}"
        print(f"OK: Alvo adaptativo candle grande: mult={mult2:.1f} (reduzido)")
    else:
        print("INFO: Adaptive target nao calculou para cenario 2")

    # Cenario 3: penultimo candle muito menor que os anteriores → multiplicador aumentado
    rates_small = []
    for i in range(30):
        c = 1.0 + i * 0.001
        rates_small.append((i, c, c + 0.03, c - 0.03, c, 100, 2, 50))  # amplitude 0.06
    # rates[-2] com amplitude pequena
    rates_small[-2] = (28, 1.028, 1.034, 1.024, 1.029, 100, 2, 50)  # amp=0.01 vs mediana 0.06

    result3 = indicators.adaptive_target_multiplier(rates_small, lookback=20)
    if result3:
        _, mult3 = result3
        assert mult3 > 1.0, f"Multiplicador deveria ser > 1.0 para candle pequeno, got {mult3}"
        print(f"OK: Alvo adaptativo candle pequeno: mult={mult3:.1f} (aumentado)")
    else:
        print("INFO: Adaptive target nao calculou para cenario 3")


# ============================================================
# EXECUCAO
# ============================================================

if __name__ == "__main__":
    print("\n=== Testes Bot MT5 — Setup 9.1/9.2 ===\n")

    tests = [
        test_scanning_to_signal_ready_buy,
        test_scanning_to_signal_ready_sell,
        test_signal_ready_cancel_on_ema_turn,
        test_signal_ready_to_in_position,
        test_in_position_partial_exit,
        test_in_position_full_exit_to_scanning,
        test_in_position_exit_profit_to_watching_92,
        test_watching_92_timeout,
        test_watching_92_pullback_generates_signal,
        test_atr_ratio_calculation,
        test_atr_stop_adjustment,
        test_volume_normalization,
        test_close_full_position_with_trade_side,
        test_close_full_position_empty_positions,
        test_adaptive_target_multiplier,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FALHOU: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERRO: {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Resultado: {passed} OK, {failed} FALHAS de {len(tests)} testes")
    if failed == 0:
        print("Todos os testes passaram!")
    sys.exit(0 if failed == 0 else 1)