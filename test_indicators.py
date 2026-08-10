"""
Testes unitários para o módulo indicators.py.
"""
import pytest
import indicators


def test_ema_calculation():
    # Menos de periodo elementos deve retornar None
    assert indicators.ema([1.0, 2.0], 5) is None

    values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    res = indicators.ema(values, 5)
    assert res is not None
    assert len(res) == 7


def test_slopes_and_turns():
    ema9_up = [1.0, 0.95, 0.90, 0.95]
    assert indicators.check_virou_para_cima(ema9_up) is True
    assert indicators.check_virou_para_baixo(ema9_up) is False

    ema9_down = [1.0, 1.05, 1.10, 1.05]
    assert indicators.check_virou_para_baixo(ema9_down) is True
    assert indicators.check_virou_para_cima(ema9_down) is False


def test_flat_filter():
    sym_info = type('obj', (object,), {'trade_tick_size': 0.00001, 'point': 0.00001})()
    # EMA9 praticamente constante
    ema9_flat = [1.10000, 1.10001, 1.10001, 1.10002, 1.10001, 1.10002]
    assert indicators.check_flat(ema9_flat, sym_info) is True

    # EMA9 com movimento forte
    ema9_moving = [1.10000, 1.10050, 1.10100, 1.10150, 1.10200, 1.10250]
    assert indicators.check_flat(ema9_moving, sym_info) is False


def test_atr():
    # Rates ficticios: (time, open, high, low, close, vol, spread, real_vol)
    rates = [
        (i, 1.0, 1.0 + (i % 3) * 0.0010, 1.0 - (i % 2) * 0.0005, 1.0 + 0.0002, 100, 0, 0)
        for i in range(70)
    ]
    atr_vals = indicators.atr(rates, period=14)
    assert atr_vals is not None
    assert len(atr_vals) > 0

    ratio_data = indicators.get_atr_ratio(rates)
    assert ratio_data is not None
    curr, avg, ratio = ratio_data
    assert curr > 0
    assert avg > 0
    assert ratio > 0


def test_pullback_92():
    candle = (0, 1.0, 1.05, 0.95, 1.02, 0, 0, 0)
    # is_long: low (0.95) <= ema9 (1.00) -> pullback True
    assert indicators.check_pullback_to_ema9(candle, 1.00, is_long=True) is True
    # is_long=False: high (1.05) >= ema9 (1.00) -> pullback True
    assert indicators.check_pullback_to_ema9(candle, 1.00, is_long=False) is True

    # sem tocar na ema9
    candle_high = (0, 1.10, 1.15, 1.08, 1.12, 0, 0, 0)
    assert indicators.check_pullback_to_ema9(candle_high, 1.00, is_long=True) is False
