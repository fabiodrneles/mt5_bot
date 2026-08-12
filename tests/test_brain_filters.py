import pandas as pd
import numpy as np
import pytest

from mt5bot.core import config
from mt5bot.data import tracker
from mt5bot.engine.indicators import (
    calculate_rvol,
    check_mtf_trend,
    check_rvol_filter,
    add_all_indicators,
)


def _df_with_volume(days=25, current_vol=1500.0, base_vol=1000.0, real=True):
    rows = []
    for i in range(days):
        vol = current_vol if i == days - 1 else base_vol
        rows.append({
            "time": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
            "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0,
            "tick_volume": vol if not real else 50,
            "real_volume": vol if real else 0,
        })
    return pd.DataFrame(rows)


def test_calculate_rvol_real_volume():
    df = _df_with_volume(current_vol=1500.0, base_vol=1000.0, real=True)
    rvol_ratio, current_vol, avg_vol = calculate_rvol(df, lookback=20)
    assert current_vol == 1500.0
    assert avg_vol == 1000.0
    assert round(rvol_ratio, 2) == 1.50


def test_calculate_rvol_tick_volume_fallback():
    df = _df_with_volume(current_vol=1200.0, base_vol=1000.0, real=False)
    rvol_ratio, current_vol, avg_vol = calculate_rvol(df, lookback=20)
    assert current_vol == 1200.0
    assert avg_vol == 1000.0
    assert round(rvol_ratio, 2) == 1.20


def test_calculate_rvol_insufficient_data_defaults_permissive():
    df = _df_with_volume(days=10)
    rvol_ratio, _, _ = calculate_rvol(df, lookback=20)
    assert rvol_ratio == 1.0


def test_check_mtf_trend_buy_confirmed(monkeypatch):
    import MetaTrader5 as mt5
    monkeypatch.setattr(config, "MTF_FILTER_ENABLED", True)
    monkeypatch.setattr(config, "AVAILABLE_TIMEFRAMES", {"H1": mt5.TIMEFRAME_H1, "M15": mt5.TIMEFRAME_M15})
    monkeypatch.setattr(config, "MTF_TIMEFRAME_MAP", {"M15": "H1"})

    def mock_copy_rates(symbol, tf, start, count):
        rates = []
        for i in range(40):
            p = 100.0 + i * 0.5
            rates.append((1000 + i, p, p + 0.5, p - 0.5, p + 0.2, 100, 0, 0))
        return rates

    monkeypatch.setattr(mt5, "copy_rates_from_pos", mock_copy_rates)
    assert check_mtf_trend("EURUSD", "M15", "BUY") is True


def test_check_mtf_trend_sell_against_disabled(monkeypatch):
    monkeypatch.setattr(config, "MTF_FILTER_ENABLED", False)
    assert check_mtf_trend("EURUSD", "M15", "SELL") is True


def test_check_rvol_filter_pass_and_block(monkeypatch):
    monkeypatch.setattr(config, "RVOL_FILTER_ENABLED", True)
    monkeypatch.setattr(config, "RVOL_LOOKBACK", 20)
    monkeypatch.setattr(config, "RVOL_THRESHOLD", 1.15)

    strong = _df_with_volume(current_vol=2000.0, base_vol=1000.0, real=True)
    assert check_rvol_filter(strong, "BUY") is True

    weak = _df_with_volume(current_vol=1000.0, base_vol=1000.0, real=True)
    assert check_rvol_filter(weak, "BUY") is False


def test_check_rvol_filter_disabled_permissive(monkeypatch):
    monkeypatch.setattr(config, "RVOL_FILTER_ENABLED", False)
    df = _df_with_volume(current_vol=0.0, base_vol=1000.0, real=True)
    assert check_rvol_filter(df, "BUY") is True


def test_mtf_and_rvol_do_not_break_evaluate_all():
    df = _df_with_volume(days=220)
    df = add_all_indicators(df)
    from mt5bot.engine.strategy import StrategyScorer
    setups, reason = StrategyScorer.evaluate_all(df, tick_size=0.01, tick_offset=1)
    # Nao deve lançar exceção; setups podem ou não existir
    assert isinstance(setups, list)
    assert isinstance(reason, str)


# ---------------------------------------------------------------------------
# Posicoes externas (manuais do usuario) — adocao e reconciliacao
# ---------------------------------------------------------------------------

def _external_position(ticket=777, position_type=None, magic=0, price_open=1.1000, sl=0.0, volume=0.10):
    import MetaTrader5 as mt5
    pos = type("Position", (object,), {
        "ticket": ticket,
        "type": position_type if position_type is not None else mt5.POSITION_TYPE_BUY,
        "magic": magic,
        "price_open": price_open,
        "sl": sl,
        "volume": volume,
    })()
    return pos


def test_register_external_position_records_manual(monkeypatch):
    import MetaTrader5 as mt5
    from mt5bot.execution.execution_manager import _register_external_position

    assert tracker.get_open_trades() == []
    _register_external_position("EURUSD", _external_position(ticket=777))
    open_trades = tracker.get_open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["ticket"] == 777
    assert open_trades[0]["setup"] == "MANUAL"
    assert open_trades[0]["side"] == "BUY"


def test_register_external_position_idempotent(monkeypatch):
    from mt5bot.execution.execution_manager import _register_external_position

    _register_external_position("EURUSD", _external_position(ticket=777))
    _register_external_position("EURUSD", _external_position(ticket=777))
    assert len(tracker.get_open_trades()) == 1


def test_register_external_position_sell_side(monkeypatch):
    import MetaTrader5 as mt5
    from mt5bot.execution.execution_manager import _register_external_position

    _register_external_position("EURUSD", _external_position(
        ticket=778, position_type=mt5.POSITION_TYPE_SELL))
    open_trades = tracker.get_open_trades()
    assert open_trades[0]["side"] == "SELL"


def test_reconcile_closed_trade_record_exit(monkeypatch):
    import MetaTrader5 as mt5
    from mt5bot.execution.execution_manager import _register_external_position, _reconcile_closed_trades

    _register_external_position("EURUSD", _external_position(
        ticket=999, price_open=1.1000))

    # Simula fechamento manual: posicao some do MT5 e ha deal de saida
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None: [])
    deal = type("Deal", (object,), {"entry": mt5.DEAL_ENTRY_OUT, "price": 1.1120})()
    monkeypatch.setattr(mt5, "history_deals_get", lambda position=None: [deal])

    _reconcile_closed_trades("EURUSD", df=None)
    closed = [t for t in tracker.get_all_trades() if t["ticket"] == 999]
    assert len(closed) == 1
    assert closed[0]["result"] == "win"
    assert closed[0]["exit_price"] == 1.1120


def test_reconcile_keeps_live_positions(monkeypatch):
    import MetaTrader5 as mt5
    from mt5bot.execution.execution_manager import _register_external_position, _reconcile_closed_trades

    _register_external_position("EURUSD", _external_position(ticket=1001))

    # Posicao ainda aberta no MT5 -> nao reconcilia
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None: [_external_position(ticket=1001)])
    _reconcile_closed_trades("EURUSD", df=None)
    assert len(tracker.get_open_trades()) == 1


def test_manage_cycle_adopts_external_and_manages(monkeypatch):
    import MetaTrader5 as mt5
    from mt5bot.execution import execution_manager

    df = _df_with_volume(days=220)
    df = add_all_indicators(df)

    monkeypatch.setattr(mt5, "positions_get", lambda **kw: [_external_position(ticket=2002)])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])
    monkeypatch.setattr(mt5, "history_deals_get", lambda position=None: [])

    execution_manager.manage_cycle("EURUSD", df, timeframe_name="H1")
    assert any(t.get("ticket") == 2002 and t.get("setup") == "MANUAL" for t in tracker.get_all_trades())