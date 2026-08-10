import pytest
import config
import indicators
import strategy

def test_calculate_rvol_real_volume():
    """Calcula RVOL corretamente usando real_volume."""
    # Lista de candles simulados com real_volume medio de 1000
    all_rates = []
    for i in range(25):
        # 20 candles com volume 1000, candle atual (indice -1) com volume 1500
        vol = 1500.0 if i == 24 else 1000.0
        candle = (100000 + i, 100.0, 105.0, 99.0, 102.0, 50, vol, 0)
        all_rates.append(candle)
        
    rvol_ratio, current_vol, avg_vol = indicators.calculate_rvol(all_rates, lookback=20)
    assert current_vol == 1500.0
    assert avg_vol == 1000.0
    assert round(rvol_ratio, 2) == 1.50

def test_calculate_rvol_tick_volume_fallback():
    """Calcula RVOL usando tick_volume quando real_volume e zero."""
    all_rates = []
    for i in range(25):
        tick_vol = 1200.0 if i == 24 else 1000.0
        candle = (100000 + i, 100.0, 105.0, 99.0, 102.0, tick_vol, 0, 0)
        all_rates.append(candle)
        
    rvol_ratio, current_vol, avg_vol = indicators.calculate_rvol(all_rates, lookback=20)
    assert current_vol == 1200.0
    assert avg_vol == 1000.0
    assert round(rvol_ratio, 2) == 1.20

def test_check_setup_93_buy():
    """Valida identificacao do Setup 9.3 de Compra."""
    # EMA9 subindo, seguida de 2 candles recuando (fechamento menor) sem virar EMA9 para baixo
    ema9_values = [10.0, 10.5, 11.0, 11.2, 11.4, 11.6]
    all_rates = [
        (1, 10.0, 11.0, 9.8, 10.8, 100, 0, 0),
        (2, 10.8, 11.2, 10.5, 11.1, 100, 0, 0),
        (3, 11.1, 11.3, 10.8, 11.2, 100, 0, 0), # Ref 9.1
        (4, 11.2, 11.25, 10.6, 10.9, 100, 0, 0), # Recuo 1 (fechamento < ref)
        (5, 10.9, 10.95, 10.4, 10.7, 100, 0, 0), # Recuo 2 (fechamento < recuo 1)
        (6, 10.7, 11.3, 10.6, 11.25, 100, 0, 0), # Candle atual rompe maxima do recuo 2 (10.95)
    ]
    
    is_93_buy = indicators.check_setup_93_buy(all_rates, ema9_values)
    assert is_93_buy is True

def test_check_mtf_trend_buy(monkeypatch):
    """Valida confirmacao da tendencia no timeframe superior (H1 quando em M15)."""
    import MetaTrader5 as mt5
    monkeypatch.setattr(config, "MTF_FILTER_ENABLED", True)
    # Simula MT5 retornando rates no H1 com EMA9 acima da EMA21 (tendencia de alta)
    def mock_copy_rates(symbol, tf, start, count):
        rates = []
        for i in range(40):
            p = 100.0 + i * 0.5
            rates.append((1000 + i, p, p + 0.5, p - 0.5, p + 0.2, 100, 0, 0))
        return rates
        
    monkeypatch.setattr(mt5, "copy_rates_from_pos", mock_copy_rates)
    mtf_ok = indicators.check_mtf_trend("EURUSD", "M15", "BUY")
    assert mtf_ok is True

import MetaTrader5 as mt5

def reset_state(symbol='TESTSYM'):
    strategy.symbol_states[symbol] = strategy.SymbolState(symbol)
    if hasattr(mt5, "_mock_positions"):
        mt5._mock_positions = []
    if hasattr(mt5, "_mock_orders"):
        mt5._mock_orders = []
    return strategy.symbol_states[symbol]

from test_strategy import make_ema9_virou_cima

def test_rvol_rejection_in_strategy(monkeypatch):
    """Ordem e rejeitada quando RVOL esta abaixo do limiar (1.15x)."""
    monkeypatch.setattr(config, "RVOL_FILTER_ENABLED", True)
    monkeypatch.setattr(indicators, "calculate_rvol", lambda *a, **k: (0.80, 800.0, 1000.0))
    s_state = reset_state()
    rates = make_ema9_virou_cima()
    candle = rates[-1]
    strategy.evaluate('TESTSYM', candle, rates)
    assert s_state.state == strategy.State.SCANNING

def test_mtf_rejection_in_strategy(monkeypatch):
    """Ordem e rejeitada quando o Filtro MTF nao confirma a tendencia."""
    monkeypatch.setattr(config, "MTF_FILTER_ENABLED", True)
    monkeypatch.setattr(indicators, "check_mtf_trend", lambda *a, **k: False)
    s_state = reset_state()
    rates = make_ema9_virou_cima()
    candle = rates[-1]
    strategy.evaluate('TESTSYM', candle, rates)
    assert s_state.state == strategy.State.SCANNING




