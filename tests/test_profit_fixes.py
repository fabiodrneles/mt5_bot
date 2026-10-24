"""Correcoes que impediam o bot de fechar operacoes no lucro.

Cobre: reconciliacao de ordens pendentes, lucro real dos deals, breakeven com
trava, setups de alvo proprio (russian_bb) saindo so por TP/SL, entrada a
mercado, 1 entrada por candle e preservacao do TP ao mover o SL.
"""
from unittest.mock import Mock

import pandas as pd
import MetaTrader5 as mt5

from mt5bot.core import config
from mt5bot.data import tracker
from mt5bot.execution import execution_manager, executor
from mt5bot.risk import risk_calculator


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _symbol_info(*_a, **_k):
    return _Obj(digits=2, point=0.01, trade_tick_size=0.01, trade_tick_value=1.0,
                volume_step=0.01, volume_min=0.01, volume_max=100.0,
                filling_mode=2, ask=0.0, bid=0.0)


def _df(ema9_down_last=False, n=5):
    df = pd.DataFrame({
        'time': pd.date_range("2023-01-01", periods=n, freq='h'),
        'open': [100.0] * n, 'high': [101.0] * n, 'low': [99.0] * n, 'close': [100.0] * n,
    })
    df['ema9_down'] = [False] * (n - 1) + [ema9_down_last]
    df['ema9_up'] = [True] * (n - 1) + [not ema9_down_last]
    df['ema9'] = 100.0
    df['sma21'] = 100.0
    df['atr'] = 1.0
    return df


def _no_daily_loss(monkeypatch):
    monkeypatch.setattr(tracker, "get_daily_pnl", lambda target_date=None: 0.0)
    monkeypatch.setattr(risk_calculator, "calculate_risk_limits", lambda balance=None: {
        "balance": 1000.0, "max_trade_risk_currency": 10.0,
        "absolute_max_trade_risk_currency": 15.0, "max_daily_loss_currency": 20.0})


# --- Reconciliacao -----------------------------------------------------------

def test_pending_order_is_not_reconciled_as_closed(monkeypatch):
    tracker.record_entry("HK50", "BUY", "9.1", 100.0, 99.0, 0.01, ticket=555)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: [])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [_Obj(ticket=555)])

    execution_manager._reconcile_closed_trades("HK50", _df())

    assert [t["ticket"] for t in tracker.get_open_trades()] == [555]


def test_cancelled_order_is_removed_not_counted_as_trade(monkeypatch):
    tracker.record_entry("HK50", "BUY", "9.1", 100.0, 99.0, 0.01, ticket=556)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: [])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])
    monkeypatch.setattr(mt5, "history_deals_get", lambda position=None, ticket=None: [])

    execution_manager._reconcile_closed_trades("HK50", _df())

    assert tracker.get_all_trades() == []


def test_reconcile_uses_real_profit_including_commission(monkeypatch):
    tracker.record_entry("HK50", "BUY", "9.1", 100.0, 99.0, 0.01, ticket=557)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: [])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])
    deals = [
        _Obj(entry=mt5.DEAL_ENTRY_IN, price=100.0, profit=0.0, commission=-0.05, swap=0.0),
        _Obj(entry=mt5.DEAL_ENTRY_OUT, price=100.01, profit=0.01, commission=-0.05, swap=0.0),
    ]
    monkeypatch.setattr(mt5, "history_deals_get", lambda position=None, ticket=None: deals)

    execution_manager._reconcile_closed_trades("HK50", _df())

    trade = tracker.get_closed_trades()[0]
    assert trade["pnl_money"] == -0.09
    assert trade["result"] == "loss"  # preco acima da entrada, mas a conta perdeu


# --- Breakeven ---------------------------------------------------------------

def test_breakeven_locks_spread_plus_tick_above_entry(monkeypatch):
    _no_daily_loss(monkeypatch)
    monkeypatch.setattr(config, "PARTIAL_EXIT_ENABLED", False)
    monkeypatch.setattr(config, "TRAILING_ENABLED", False)
    monkeypatch.setattr(mt5, "symbol_info", _symbol_info)
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=101.50, ask=101.55))
    pos = _Obj(type=mt5.POSITION_TYPE_BUY, ticket=10, volume=0.01, price_open=99.0,
               sl=98.0, tp=0.0, profit=1.0)
    modify = Mock()
    monkeypatch.setattr(executor, "modify_position_sl", modify)

    df = _df()
    df.loc[df.index[-1], 'close'] = 100.5  # ganho 1.5 >= 1 ATR
    execution_manager._manage_position("HK50", pos, df)

    new_sl = modify.call_args[0][2]
    assert abs(new_sl - (99.0 + 0.05 + 0.01)) < 1e-9


# --- Setups de alvo proprio --------------------------------------------------

def test_russian_bb_position_is_left_to_tp_sl(monkeypatch):
    _no_daily_loss(monkeypatch)
    tracker.record_entry("HK50", "BUY", "russian_bb", 100.0, 95.0, 0.01, ticket=20)
    monkeypatch.setattr(mt5, "symbol_info", _symbol_info)
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=100.0, ask=100.05))
    modify, close = Mock(), Mock()
    monkeypatch.setattr(executor, "modify_position_sl", modify)
    monkeypatch.setattr(executor, "close_full_position", close)
    pos = _Obj(type=mt5.POSITION_TYPE_BUY, ticket=20, volume=0.01, price_open=100.0,
               sl=95.0, tp=110.0, profit=0.0)

    # EMA9 apontando para baixo: em reversao a media isso e o normal
    execution_manager._manage_position("HK50", pos, _df(ema9_down_last=True))

    modify.assert_not_called()
    close.assert_not_called()


def test_ema9_exit_closes_at_market_when_price_already_below_low(monkeypatch):
    _no_daily_loss(monkeypatch)
    monkeypatch.setattr(config, "PARTIAL_EXIT_ENABLED", False)
    monkeypatch.setattr(config, "ENABLE_BREAKEVEN", False)
    monkeypatch.setattr(config, "TRAILING_ENABLED", False)
    monkeypatch.setattr(mt5, "symbol_info", _symbol_info)
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=98.0, ask=98.05))
    modify, close = Mock(), Mock()
    monkeypatch.setattr(executor, "modify_position_sl", modify)
    monkeypatch.setattr(executor, "close_full_position", close)
    pos = _Obj(type=mt5.POSITION_TYPE_BUY, ticket=21, volume=0.01, price_open=100.0,
               sl=95.0, tp=0.0, profit=0.0)

    execution_manager._manage_position("HK50", pos, _df(ema9_down_last=True))

    close.assert_called_once()
    modify.assert_not_called()


# --- Entrada -----------------------------------------------------------------

def _scan_env(monkeypatch, setup):
    _no_daily_loss(monkeypatch)
    monkeypatch.setattr(risk_calculator, "get_trading_session_info", lambda symbol=None: {"is_open": True})
    monkeypatch.setattr(mt5, "symbol_info", _symbol_info)
    monkeypatch.setattr(execution_manager.StrategyScorer, "evaluate_all",
                        staticmethod(lambda *a, **k: ([dict(setup)], "")))
    monkeypatch.setattr(execution_manager, "check_mtf_trend", lambda *a: True)
    monkeypatch.setattr(execution_manager, "check_rvol_filter", lambda *a: True)
    monkeypatch.setattr(risk_calculator, "calculate_position_size",
                        lambda **k: (0.01, 0.1, True, "OK"))
    ok = _Obj(retcode=mt5.TRADE_RETCODE_DONE, order=777)
    market, stop = Mock(return_value=ok), Mock(return_value=ok)
    monkeypatch.setattr(executor, "place_market_order", market)
    monkeypatch.setattr(executor, "place_buy_stop", stop)
    monkeypatch.setattr(execution_manager._scan_and_execute, "last_traded_candle", {}, raising=False)
    return market, stop


def test_russian_bb_enters_at_market_with_tp(monkeypatch):
    setup = {"setup": "russian_bb", "action": "buy", "trigger_price": 100.0,
             "stop_loss": 95.0, "target": 110.0, "score": 100}
    market, stop = _scan_env(monkeypatch, setup)

    execution_manager._scan_and_execute("HK50", _df())

    stop.assert_not_called()
    market.assert_called_once()
    assert market.call_args.kwargs["tp_price"] == 110.0


def test_only_one_entry_per_candle(monkeypatch):
    setup = {"setup": "9.1", "action": "buy", "trigger_price": 101.01,
             "stop_loss": 99.0, "score": 10}
    market, stop = _scan_env(monkeypatch, setup)
    df = _df()

    execution_manager._scan_and_execute("HK50", df)
    execution_manager._scan_and_execute("HK50", df)  # mesmo candle, 1s depois

    assert stop.call_count == 1
    assert stop.call_args.kwargs["tp_price"] is None  # 9.x segue saindo por trailing


def test_modify_sl_preserves_existing_tp(monkeypatch):
    monkeypatch.setattr(mt5, "symbol_info", _symbol_info)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: [_Obj(ticket=30, tp=110.0)])
    sent = {}
    monkeypatch.setattr(mt5, "order_send", lambda req: sent.update(req) or _Obj(retcode=mt5.TRADE_RETCODE_DONE, order=1))

    executor.modify_position_sl(30, "HK50", 99.5)

    assert sent["tp"] == 110.0
    assert sent["sl"] == 99.5
