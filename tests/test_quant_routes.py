"""Rotas quant (v2.10.0): HK50 H4 PULLB e US500 D1 RSI2MR.

Cobre os sinais (identicos ao backtest), a entrada a mercado com lote minimo e
SL/TP, as travas de risco/margem, a saida pela regra e o isolamento em relacao
a posicoes manuais do usuario e ao caminho antigo (EMA9/trailing).
"""
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import pytest

from mt5bot.core import config
from mt5bot.data import tracker
from mt5bot.engine import quant_setups
from mt5bot.execution import execution_manager, quant_manager
from mt5bot.risk import risk_calculator

H4 = 14400
D1 = 86400


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _trend_df(n=300, tf=H4, slope=1.0, start=2_000_000_000):
    t = start - start % tf
    close = 1000.0 + slope * np.arange(n)
    df = pd.DataFrame({
        "time": pd.to_datetime(t + tf * np.arange(n), unit="s"),
        "open": close - 0.5 * slope, "high": close + 2.0, "low": close - 2.0, "close": close,
    })
    return df


def _pullback_df():
    """Tendencia de alta; o ultimo candle toca a EMA20 e fecha acima dela."""
    df = _trend_df()
    last = df.index[-1]
    df.loc[last, "low"] = df.loc[last, "close"] - 15.0
    return df


def _rsi2_dip_df():
    """Alta longa (acima da SMA200) seguida de 2 quedas fortes: IFR2 < 5."""
    df = _trend_df(tf=D1)
    for k, drop in ((-2, 8.0), (-1, 16.0)):
        i = df.index[k]
        df.loc[i, "close"] = df.loc[df.index[-3], "close"] - drop
        df.loc[i, "low"] = df.loc[i, "close"] - 1.0
    return df


@pytest.fixture
def market(monkeypatch):
    """MT5 simulado: saldo $16.26, HK50 com margem de $0.15 e risco de $0.21."""
    state = {"sent": [], "closed": [], "positions": [], "balance": 16.26, "free": 14.35,
             "loss": -0.21, "margin": 0.15, "tick_time": None, "forming_time": None}

    def tick(symbol):
        return _Obj(bid=23000.0, ask=23004.5, time=state["tick_time"])

    monkeypatch.setattr(mt5, "symbol_info_tick", tick)
    monkeypatch.setattr(mt5, "symbol_info", lambda s: _Obj(
        digits=2, point=0.01, trade_tick_size=0.01, volume_step=0.01, volume_min=0.01,
        volume_max=100.0, filling_mode=2, trade_stops_level=200))
    monkeypatch.setattr(mt5, "account_info", lambda: _Obj(balance=state["balance"], margin_free=state["free"]))
    monkeypatch.setattr(mt5, "order_calc_profit", lambda *a: state["loss"], raising=False)
    monkeypatch.setattr(mt5, "order_calc_margin", lambda *a: state["margin"], raising=False)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: list(state["positions"]))
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda s, tf, start, count: (
        [] if state["forming_time"] is None else np.array([(state["forming_time"],)], dtype=[("time", "i8")])))

    def send(req):
        state["sent"].append(req)
        return _Obj(retcode=mt5.TRADE_RETCODE_DONE, order=777, comment="ok")
    monkeypatch.setattr(mt5, "order_send", send)
    monkeypatch.setattr(tracker, "get_daily_pnl", lambda target_date=None: 0.0)
    monkeypatch.setattr(risk_calculator, "calculate_risk_limits", lambda balance=None: {
        "balance": 16.26, "max_trade_risk_currency": 0.16,
        "absolute_max_trade_risk_currency": 0.24, "max_daily_loss_currency": 0.33})
    quant_manager._last_signal_candle.clear()
    return state


def _open_at_next_bar(state, df, tf=H4, delay=30, gap=0):
    """Candle seguinte ao de sinal abriu (gap = fim de semana/pausa) ha `delay` s."""
    state["forming_time"] = int(df["time"].iloc[-1].timestamp()) + tf + gap
    state["tick_time"] = state["forming_time"] + delay


# --- Sinais -------------------------------------------------------------------

def test_pullb_buy_signal_on_pullback_to_ema20():
    sig = quant_setups.evaluate("PULLB", _pullback_df(), {"sl_atr": 1.0, "tp_r": 2.0})
    assert sig["action"] == "buy"
    assert sig["tp_dist"] == pytest.approx(2 * sig["sl_dist"])


def test_pullb_no_signal_without_touch():
    assert quant_setups.evaluate("PULLB", _trend_df(), {}) is None


def test_rsi2_buy_signal_on_dip_above_sma200():
    sig = quant_setups.evaluate("RSI2MR", _rsi2_dip_df(), {"rsi_level": 5.0, "sl_atr": 2.0})
    assert sig["action"] == "buy" and sig["tp_dist"] is None


def test_rsi2_exit_when_close_crosses_sma5():
    df = _trend_df(tf=D1)
    assert quant_setups.should_exit("RSI2MR", df, is_buy=True, params={})
    assert not quant_setups.should_exit("RSI2MR", df, is_buy=False, params={})


# --- Entrada ------------------------------------------------------------------

def test_quant_entry_market_order_min_lot_with_sl_tp(market):
    df = _pullback_df()
    _open_at_next_bar(market, df)
    route = config.QUANT_ROUTES["HK50"]

    state = quant_manager.quant_cycle("HK50", df, "H4", route)

    assert state.startswith("🟢 EM POSIÇÃO")
    req = market["sent"][-1]
    assert req["action"] == mt5.TRADE_ACTION_DEAL and req["type"] == mt5.ORDER_TYPE_BUY
    assert req["volume"] == 0.01 and req["magic"] == config.MAGIC
    assert req["comment"] == "Q PULLB"
    assert req["sl"] < req["price"] < req["tp"]
    assert (req["tp"] - req["price"]) == pytest.approx(2 * (req["price"] - req["sl"]), abs=0.02)
    assert tracker.get_open_trades()[0]["setup"] == "PULLB"


def test_quant_rejects_when_stop_loss_exceeds_balance_risk(market):
    market["loss"] = -1.63  # US500 D1 com $16: 10% do saldo
    df = _pullback_df()
    _open_at_next_bar(market, df)

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state == "🟡 SINAL REJEITADO" and market["sent"] == []


def test_quant_rejects_when_margin_reserve_would_be_broken(market):
    market["free"] = 0.5
    df = _pullback_df()
    _open_at_next_bar(market, df)

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state == "🟡 SEM MARGEM" and market["sent"] == []


def test_quant_signal_expires_if_entry_too_late(market):
    df = _pullback_df()
    _open_at_next_bar(market, df, delay=3 * 3600)

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state == "🔵 SINAL EXPIRADO" and market["sent"] == []


def test_quant_waits_for_market_open_without_consuming_signal(market):
    df = _pullback_df()
    market["forming_time"] = int(df["time"].iloc[-1].timestamp())  # candle seguinte ainda nao abriu
    market["tick_time"] = market["forming_time"] + 100

    assert quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"]) == "⏳ AGUARDANDO MERCADO"
    _open_at_next_bar(market, df)
    assert quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"]).startswith("🟢")


def test_quant_enters_on_first_candle_after_weekend_gap(market):
    df = _pullback_df()
    _open_at_next_bar(market, df, gap=2 * D1, delay=60)

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state.startswith("🟢 EM POSIÇÃO")


def test_quant_one_attempt_per_candle(market):
    df = _pullback_df()
    _open_at_next_bar(market, df)
    market["free"] = 0.5
    quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])
    market["free"] = 14.35

    assert quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"]) == "🔵 AGUARDANDO PRÓXIMO CANDLE"
    assert market["sent"] == []


def test_manual_position_is_ignored_and_untouched(market):
    manual = _Obj(ticket=235435813, magic=0, comment="", type=mt5.POSITION_TYPE_BUY,
                  time=0, volume=0.01, price_open=24380.26, sl=0.0, tp=24552.84, profit=-1.63)
    market["positions"] = [manual]
    df = _pullback_df()
    _open_at_next_bar(market, df)

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state.startswith("🟢 EM POSIÇÃO")
    assert all(r.get("position") != manual.ticket for r in market["sent"])


# --- Gestao da posicao ----------------------------------------------------------

def _quant_pos(df, tf, bars_ago_entry, is_buy=True, setup="RSI2MR"):
    entry_bar = int(df["time"].iloc[-1].timestamp()) - (bars_ago_entry - 1) * tf
    return _Obj(ticket=888, magic=config.MAGIC, comment=f"Q {setup}", time=entry_bar + 60,
                type=mt5.POSITION_TYPE_BUY if is_buy else mt5.POSITION_TYPE_SELL,
                volume=0.01, price_open=1000.0, sl=900.0, tp=0.0, profit=0.0)


def test_rsi2_does_not_exit_on_signal_candle(market):
    df = _trend_df(tf=D1)  # close > SMA5: regra de saida verdadeira
    pos = _quant_pos(df, D1, bars_ago_entry=0)  # entrou depois do ultimo candle fechado
    market["positions"] = [pos]

    state = quant_manager.quant_cycle("US500", df, "D1", config.QUANT_ROUTES["US500"])

    assert state.startswith("🟢 IN_POSITION") and market["sent"] == []


def test_rsi2_exits_by_rule_after_entry_candle_closes(market):
    df = _trend_df(tf=D1)
    market["positions"] = [_quant_pos(df, D1, bars_ago_entry=1)]

    state = quant_manager.quant_cycle("US500", df, "D1", config.QUANT_ROUTES["US500"])

    assert state == "🟢 SAIDA RSI2MR"
    assert market["sent"][-1]["position"] == 888


def test_rsi2_time_exit_after_max_bars(market):
    df = _trend_df(tf=D1)
    market["positions"] = [_quant_pos(df, D1, bars_ago_entry=15, is_buy=False)]

    state = quant_manager.quant_cycle("US500", df, "D1", config.QUANT_ROUTES["US500"])

    assert state == "🟢 SAIDA RSI2MR (tempo)"


def test_pullb_position_left_to_sl_tp(market):
    df = _trend_df()
    market["positions"] = [_quant_pos(df, H4, bars_ago_entry=30, setup="PULLB")]

    state = quant_manager.quant_cycle("HK50", df, "H4", config.QUANT_ROUTES["HK50"])

    assert state.startswith("🟢 IN_POSITION (PULLB") and market["sent"] == []


# --- Roteamento -----------------------------------------------------------------

def test_route_only_matches_configured_timeframe():
    assert quant_manager.get_route("HK50", "H4")["setup"] == "PULLB"
    assert quant_manager.get_route("HK50", "H1") is None
    assert quant_manager.get_route("EURUSD", "H4") is None


def test_legacy_path_does_not_manage_quant_positions(market, monkeypatch):
    df = _trend_df(n=50, tf=3600)
    df["ema9_down"] = True; df["ema9_up"] = False
    df["atr"] = 1.0
    market["positions"] = [_quant_pos(df, 3600, bars_ago_entry=3, setup="PULLB")]
    called = []
    monkeypatch.setattr(execution_manager, "_manage_position", lambda *a, **k: called.append(a))
    monkeypatch.setattr(execution_manager, "_scan_and_execute", lambda *a, **k: "🔵 SCANNING")

    execution_manager.manage_cycle("HK50", df, timeframe_name="H1")

    assert called == []
