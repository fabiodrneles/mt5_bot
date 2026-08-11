import numpy as np
import pandas as pd
import pytest

import config
from brain.indicators import (
    add_all_indicators,
    calculate_rsi,
    calculate_sar,
    calculate_vwap,
    check_ifr9_filter,
    check_mm50_filter,
    check_vwap_filter,
    fib_extension_targets,
    swing_levels,
)
from brain.setups import StrategyScorer


def _make_df(closes, highs=None, lows=None, opens=None):
    n = len(closes)
    highs = highs if highs is not None else [c * 1.02 for c in closes]
    lows = lows if lows is not None else [c * 0.98 for c in closes]
    opens = opens if opens is not None else closes
    df = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="h"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
    })
    return add_all_indicators(df)


# ---------------------------------------------------------------------------
# Indicadores novos
# ---------------------------------------------------------------------------

def test_calculate_rsi_basic():
    # Sobe sempre -> IFR alto; desce sempre -> IFR baixo
    up = pd.Series(np.arange(1.0, 30.0, 1.0))
    rsi_up = calculate_rsi(up, 2)
    assert rsi_up.iloc[-1] > 90

    down = pd.Series(np.arange(30.0, 1.0, -1.0))
    rsi_down = calculate_rsi(down, 2)
    assert rsi_down.iloc[-1] < 10


def test_calculate_sar_forms_series():
    closes = [100.0 + i for i in range(30)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    df = pd.DataFrame({"high": highs, "low": lows})
    sar = calculate_sar(df)
    assert len(sar) == 30
    assert sar.iloc[-1] < df['low'].iloc[-1]  # uptrend -> SAR abaixo


# ---------------------------------------------------------------------------
# Setups do livro (avaliacao pontual via evaluate_all)
# ---------------------------------------------------------------------------

def test_setup_dinapoli_buy_trigger():
    # Fundo1 (low[-3]) abaixo do candle anterior (novo minimo); Fundo2 (low[-2])
    # mais alto que o Fundo1 (minimo ascendente) e fechando acima da EMA12 deslocada.
    # lows:  low[-6..-5] nivel, low[-4]=100.0, low[-3]=98.0 (fundo 1),
    #        low[-2]=98.5 (fundo 2 mais alto)
    closes = [101, 102, 103, 104, 105, 106, 105.5, 103, 101, 100, 100.5, 101.5]
    lows = [100.6, 101.6, 102.6, 103.6, 104.6, 105.6, 105.0, 100.5, 99.5, 98.0, 98.6, 99.6]
    highs = [c + 0.5 for c in closes]
    df = _make_df(closes, highs, lows)
    # Em 12 candles a EMA12 deslocada ainda e NaN; forçamos para isolar a logica.
    df.loc[df.index[-2], 'ema12_displaced'] = 98.0
    assert df['low'].iloc[-3] < df['low'].iloc[-4]   # fundo 1 = novo minimo
    assert df['low'].iloc[-2] >= df['low'].iloc[-3]  # fundo 2 mais alto
    setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, tick_offset=1)
    names = [s["setup"] for s in setups]
    assert "DiNapoli" in names


def test_setup_ifr2_buy_trigger():
    # Queda forte no fim para IFR2 <=5, com EMA50 subindo antes
    closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
              110, 111, 112, 113, 112, 111, 110, 109, 108, 106, 104, 102]
    df = _make_df(closes)
    # forcar rsi2 <=5, EMA50 abaixo do preco e subindo, MM13 abaixo
    df.loc[df.index[-1], 'rsi2'] = 3.0
    df.loc[df.index[-1], 'ema50'] = df['close'].iloc[-1] - 2.0
    df.loc[df.index[-1], 'ema50_up'] = True
    df.loc[df.index[-1], 'sma13'] = df['close'].iloc[-1] - 1.0
    setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, tick_offset=1)
    names = [s["setup"] for s in setups]
    assert "IFR2" in names


def test_setup_sar_buy_trigger():
    closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    df = _make_df(closes, highs, lows)
    df.loc[df.index[-1], 'sar'] = df['low'].iloc[-1] - 1.0   # SAR sob o preço
    df.loc[df.index[-1], 'rsi14'] = 60.0
    df.loc[df.index[-1], 'sma13'] = df['close'].iloc[-1] - 1.0
    setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, tick_offset=1)
    names = [s["setup"] for s in setups]
    assert "SAR" in names


def test_setup_rompimento_falso_buy_trigger():
    # Suporte = low[-4] = 99.0. candle[-2] fecha abaixo (98.9 -> rompe).
    # candle[-1] fecha acima de 99.0 (falhou), com low[-1] < 99.0 (mecha que violou).
    closes = [101, 101.5, 102, 101, 101.5, 101.0, 100.5, 100.0, 99.0, 99.2, 98.9, 99.5]
    lows = [100.5, 101.0, 101.5, 100.5, 101.0, 100.5, 100.0, 99.0, 99.1, 99.0, 98.8, 98.9]
    highs = [c + 0.5 for c in closes]
    df = _make_df(closes, highs, lows)
    sup = df['low'].iloc[-4]
    assert df['close'].iloc[-2] < sup     # candle anterior rompeu o suporte
    assert df['close'].iloc[-1] > sup     # volta para dentro
    assert df['low'].iloc[-1] < sup       # mecha violou o suporte
    setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, tick_offset=1)
    names = [s["setup"] for s in setups]
    assert "RompFalso" in names


def test_all_book_setups_in_config():
    for name in ["DiNapoli", "IFR2", "SAR", "RompFalso"]:
        assert config.CONFIG_SETUPS.get(name, False) is True


# ---------------------------------------------------------------------------
# Filtros macro Fase 2.5: MM50, IFR9, VWAP
# ---------------------------------------------------------------------------

def _trend_df(shares=80, start=100.0, vol=1000.0, daily=False):
    n = max(60, shares)
    closes = [start + i * 0.5 for i in range(n)]
    if daily:
        times = pd.date_range("2026-01-01", periods=n, freq="D")
    else:
        times = pd.date_range("2026-01-01", periods=n, freq="h")
    df = pd.DataFrame({
        "time": times,
        "open": closes, "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes], "close": closes,
        "tick_volume": [vol] * n,
    })
    return add_all_indicators(df)


def test_calculate_vwap_daily_anchor():
    # Ancorado por dia: vol constante -> VWAP = preco tipico medio do dia
    df = _trend_df(start=100.0, daily=True)
    vwap = calculate_vwap(df)
    assert not np.isnan(vwap.iloc[-1])


def test_calculate_vwap_missing_columns_permissive():
    bad = pd.DataFrame({"close": [1.0, 2.0]})
    vwap = calculate_vwap(bad)
    assert np.isnan(vwap.iloc[-1])


def test_mm50_filter_buy_above_sma50(monkeypatch):
    monkeypatch.setattr(config, "MM50_ENABLED", True)
    df = _trend_df(start=100.0)  # uptrend, close > sma50
    assert check_mm50_filter(df, "BUY") is True
    assert check_mm50_filter(df, "SELL") is False


def test_mm50_filter_disabled_permissive(monkeypatch):
    monkeypatch.setattr(config, "MM50_ENABLED", False)
    df = _trend_df(start=100.0)
    assert check_mm50_filter(df, "SELL") is True


def test_ifr9_filter_buy_exit_oversold(monkeypatch):
    monkeypatch.setattr(config, "IFR9_ENABLED", True)
    # series em V com reversao no fim -> IFR9 sobe saindo de <=30
    closes = [100 - i * 0.6 for i in range(25)] + [72.5, 73.5, 74.5]
    df = pd.DataFrame({"time": pd.date_range("2026-01-01", periods=len(closes), freq="h"),
                       "open": closes, "high": [c + 0.2 for c in closes],
                       "low": [c - 0.2 for c in closes], "close": closes,
                       "tick_volume": [1000] * len(closes)})
    df = add_all_indicators(df)
    assert check_ifr9_filter(df, "BUY") is True


def test_ifr9_disabled_permissive(monkeypatch):
    monkeypatch.setattr(config, "IFR9_ENABLED", False)
    df = _trend_df()
    assert check_ifr9_filter(df, "BUY") is True


def test_vwap_filter_rejects_stretched(monkeypatch):
    monkeypatch.setattr(config, "VWAP_ENABLED", True)
    monkeypatch.setattr(config, "VWAP_MAX_DEVIATION_ATR", 0.5)
    # Close muito acima da VWAP (spike) -> desvio > 0.5 ATR -> vetado
    n = 40
    closes = [100.0 + i * 0.2 for i in range(n)]
    closes[-1] = closes[-2] + 5.0  # spike
    df = pd.DataFrame({"time": pd.date_range("2026-01-01", periods=n, freq="h"),
                       "open": closes, "high": [c + 0.5 for c in closes],
                       "low": [c - 0.5 for c in closes], "close": closes,
                       "tick_volume": [1000] * n})
    df = add_all_indicators(df)
    assert check_vwap_filter(df, "BUY") is False  # spike esticou alem de 0.5 ATR -> vetado


def test_vwap_disabled_permissive(monkeypatch):
    monkeypatch.setattr(config, "VWAP_ENABLED", False)
    df = _trend_df()
    assert check_vwap_filter(df, "BUY") is True


# ---------------------------------------------------------------------------
# Alvos Fibonacci (spec 5.6): swing_levels + fib_extension_targets
# ---------------------------------------------------------------------------

def test_swing_levels_high_low():
    n = 30
    closes = list(range(90, 120))  # 30 candles
    highs = [c + 3 for c in closes]
    lows = [c - 2 for c in closes]
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
    sh, sl = swing_levels(df, lookback=20)
    assert sh == 122.0               # maior high dos ultimos 20 (100..119 + 3)
    assert sl == 98.0                # menor low dos ultimos 20 (100..119 - 2)
    assert sh > sl


def test_swing_levels_insufficient():
    sh, sl = swing_levels(pd.DataFrame({"high": [], "low": []}), lookback=20)
    assert np.isnan(sh) and np.isnan(sl)


def test_fib_long_targets():
    t1, t2 = fib_extension_targets(entry=100.0, swing_high=110.0, swing_low=95.0, is_long=True)
    assert t1 == 100.0 + 15.0           # 1.0x amplitude
    assert t2 == pytest.approx(100.0 + 15.0 * 1.618)


def test_fib_short_targets():
    t1, t2 = fib_extension_targets(entry=100.0, swing_high=110.0, swing_low=95.0, is_long=False)
    assert t1 == 100.0 - 15.0
    assert t2 == pytest.approx(100.0 - 15.0 * 1.618)


def test_fib_invalid_amplitude_returns_none():
    assert fib_extension_targets(entry=100.0, swing_high=95.0, swing_low=110.0, is_long=False) == (None, None)
    assert fib_extension_targets(entry=100.0, swing_high=np.nan, swing_low=95.0, is_long=True) == (None, None)