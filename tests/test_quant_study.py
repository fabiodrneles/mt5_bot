"""Rotas quant em ESTUDO (mode = "study"): sinais e saidas reais, ordens virtuais (cap. 14 do guia)."""
import copy

import MetaTrader5 as mt5
import pytest

from mt5bot.core import config, user_config
from mt5bot.execution import quant_manager, quant_study
from test_quant_routes import D1, _Obj, _open_at_next_bar, _rsi2_dip_df, _trend_df, market  # noqa: F401


@pytest.fixture
def study(market, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setattr(quant_study, "_path", lambda: str(tmp_path / "quant_study.json"))
    # cotacao coerente com os candles sinteticos (~1.000-1.300 pontos)
    px = float(_rsi2_dip_df()["close"].iloc[-1])
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=px, ask=px + 0.5, time=market["tick_time"]))
    return market


def test_us100_is_configured_as_study_route():
    route = config.QUANT_ROUTES["US100"]
    assert quant_manager.is_study_route(route)
    assert route["setup"] == "RSI2MR" and route["params"] == config.QUANT_ROUTES["US500"]["params"]


def test_study_entry_is_virtual_and_sends_no_order(study):
    df = _rsi2_dip_df()
    _open_at_next_bar(study, df, tf=D1)
    study["loss"] = -5.20  # stop do US100 no lote minimo: muito acima do limite com $16

    state = quant_manager.quant_cycle("US100", df, "D1", config.QUANT_ROUTES["US100"])

    assert state.startswith("📘 ESTUDO: ENTRADA VIRTUAL")
    assert study["sent"] == []  # nada foi ao MT5, mesmo com risco acima do limite
    trade = quant_study.load()[0]
    assert trade["status"] == "open" and trade["side"] == "BUY" and trade["sl"] < trade["entry_price"]
    assert trade["risk_usd"] == pytest.approx(5.20)


def test_study_exit_by_rule_records_result(study):
    df = _rsi2_dip_df()
    _open_at_next_bar(study, df, tf=D1)
    quant_manager.quant_cycle("US100", df, "D1", config.QUANT_ROUTES["US100"])
    entry_bar = quant_study.load()[0]["entry_bar"]
    # um candle fechado depois da entrada, ja acima da SMA5: a regra manda sair
    up = _trend_df(n=301, tf=D1, start=entry_bar - 300 * D1)
    study["loss"] = 0.35

    state = quant_manager.quant_cycle("US100", up, "D1", config.QUANT_ROUTES["US100"])

    assert state == "📘 ESTUDO: SAÍDA VIRTUAL (regra de saida)"
    trade = quant_study.load()[0]
    assert trade["status"] == "closed" and trade["result_usd"] == pytest.approx(0.35)
    assert study["sent"] == [] and study["closed"] == []
    assert quant_study.summary("US100") == {"n": 1, "wins": 1, "net": 0.35, "open": 0}


def test_config_toml_switches_route_mode(tmp_path):
    ns = {"QUANT_ROUTES": copy.deepcopy(config.QUANT_ROUTES)}
    path = tmp_path / "config.toml"
    path.write_text('[routes.US100]\nmode = "live"\n', encoding="utf-8")
    assert user_config.apply(ns, str(path)) == []
    assert not quant_manager.is_study_route(ns["QUANT_ROUTES"]["US100"])

    path.write_text('[routes.US100]\nmode = "turbo"\n', encoding="utf-8")
    ns = {"QUANT_ROUTES": copy.deepcopy(config.QUANT_ROUTES)}
    errors = user_config.apply(ns, str(path))
    assert errors and "routes.US100.mode" in errors[0]
    assert quant_manager.is_study_route(ns["QUANT_ROUTES"]["US100"])  # valor invalido: mantem o estudo


def _hourly_df(last_open, n=300):
    """Candles H1 terminando no candle que abre em `last_open` (horario do servidor)."""
    import numpy as np
    import pandas as pd
    t = pd.date_range(end=last_open, periods=n, freq="h")
    close = 150.0 + np.sin(np.arange(n) / 5.0)
    return pd.DataFrame({"time": t, "open": close, "high": close + 0.2, "low": close - 0.2, "close": close})


def test_hour_setup_fires_only_on_the_bar_before_monday_01h():
    from mt5bot.engine import quant_setups
    params = config.QUANT_ROUTES["USDJPY"]["params"]
    # 2026-10-19 e segunda: o candle de sinal e o das 00h (entrada na abertura das 01h)
    sig = quant_setups.evaluate("HOUR", _hourly_df("2026-10-19 00:00"), params)
    assert sig["action"] == "buy" and sig["tp_dist"] is None and sig["sl_dist"] > 0
    assert quant_setups.evaluate("HOUR", _hourly_df("2026-10-19 01:00"), params) is None
    assert quant_setups.evaluate("HOUR", _hourly_df("2026-10-20 00:00"), params) is None  # terca


def test_usdjpy_hour_route_is_study_and_exits_after_one_bar(study, monkeypatch):
    route = config.QUANT_ROUTES["USDJPY"]
    assert quant_manager.is_study_route(route) and route["params"]["max_bars"] == 1
    df = _hourly_df("2026-10-19 00:00")
    px = float(df["close"].iloc[-1])
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=px, ask=px + 0.01, time=study["tick_time"]))
    _open_at_next_bar(study, df, tf=3600)
    state = quant_manager.quant_cycle("USDJPY", df, "H1", route)
    assert state.startswith("📘 ESTUDO: ENTRADA VIRTUAL") and study["sent"] == []
    # fecha o candle das 01h: sai pelo tempo (1 candle)
    df2 = _hourly_df("2026-10-19 01:00")
    state = quant_manager.quant_cycle("USDJPY", df2, "H1", route)
    assert state == "📘 ESTUDO: SAÍDA VIRTUAL (tempo)"
    assert study["sent"] == []


def test_two_routes_on_the_same_symbol_are_independent():
    routes = config.QUANT_ROUTES
    assert quant_manager.route_symbol("USDJPY_IFR2", routes["USDJPY_IFR2"]) == "USDJPY"
    assert quant_manager.get_route("USDJPY", "H1")["setup"] == "HOUR"
    assert quant_manager.get_route("USDJPY", "D1")["setup"] == "STORMER"
    assert quant_manager.signal_key("USDJPY", 3600) != quant_manager.signal_key("USDJPY", 86400)


def test_stormer_signal_buys_extreme_rsi2_with_target_at_two_bar_high():
    import numpy as np
    import pandas as pd
    from mt5bot.engine import quant_setups
    n = 60
    close = np.r_[np.linspace(150, 160, n - 3), [157.0, 154.0, 151.0]]  # tres quedas fortes: IFR2 ~ 0
    df = pd.DataFrame({"time": pd.date_range("2026-01-01", periods=n, freq="D"), "open": close,
                       "high": close + 0.5, "low": close - 0.5, "close": close})
    sig = quant_setups.evaluate("STORMER", df, config.QUANT_ROUTES["USDJPY_IFR2"]["params"])
    assert sig["action"] == "buy" and sig["sl_dist"] > 0
    assert sig["tp_dist"] == pytest.approx(max(df["high"].iloc[-2:]) - close[-1])
    up = df.assign(close=np.linspace(150, 170, n))
    assert quant_setups.evaluate("STORMER", up, config.QUANT_ROUTES["USDJPY_IFR2"]["params"]) is None


def test_stormer_study_route_enters_virtually_on_the_d1_without_touching_the_h1_route(study, monkeypatch):
    import numpy as np
    import pandas as pd
    n = 300
    close = np.r_[np.linspace(140, 160, n - 3), [157.0, 154.0, 151.0]]
    t0 = pd.Timestamp("2026-10-16")
    df = pd.DataFrame({"time": pd.date_range(end=t0, periods=n, freq="D"), "open": close,
                       "high": close + 0.5, "low": close - 0.5, "close": close})
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=151.0, ask=151.01, time=study["tick_time"]))
    _open_at_next_bar(study, df, tf=86400)
    state = quant_manager.quant_cycle("USDJPY", df, "D1", config.QUANT_ROUTES["USDJPY_IFR2"])
    assert state.startswith("📘 ESTUDO: ENTRADA VIRTUAL (STORMER BUY)") and study["sent"] == []
    trade = quant_study.load()[0]
    assert trade["setup"] == "STORMER" and trade["tp"] is not None
