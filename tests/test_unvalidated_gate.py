"""Setups nao validados fora do modo ao vivo por padrao (spec 005 FR-2, D5)."""
import logging

import MetaTrader5 as mt5

from mt5bot.core import config, telemetry, user_config
from mt5bot.execution import execution_manager

from test_profit_fixes import _df, _scan_env


def _flat(monkeypatch):
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None, ticket=None: [])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])
    execution_manager._unvalidated_warned.clear()


def test_classic_setup_does_not_trade_live_by_default(monkeypatch, caplog):  # AC-2
    setup = {"setup": "9.1", "action": "buy", "trigger_price": 101.01, "stop_loss": 99.0, "score": 10}
    market, stop = _scan_env(monkeypatch, setup)
    _flat(monkeypatch)
    assert config.ALLOW_UNVALIDATED_LIVE is False

    with caplog.at_level(logging.WARNING):
        state = execution_manager.manage_cycle("EURUSD", _df(), timeframe_name="H1")
        execution_manager.manage_cycle("EURUSD", _df(), timeframe_name="H1")

    assert state == "🔒 SÓ SIMULAÇÃO"
    stop.assert_not_called()
    market.assert_not_called()
    assert caplog.text.count("/study EURUSD H1") == 1          # explica uma vez, sem inundar o log
    assert "allow_unvalidated_live = true" in caplog.text


def test_option_restores_classic_live_trading(monkeypatch):  # AC-3
    setup = {"setup": "9.1", "action": "buy", "trigger_price": 101.01, "stop_loss": 99.0, "score": 10}
    market, stop = _scan_env(monkeypatch, setup)
    _flat(monkeypatch)
    monkeypatch.setattr(config, "ALLOW_UNVALIDATED_LIVE", True)

    execution_manager.manage_cycle("EURUSD", _df(), timeframe_name="H1")

    stop.assert_called_once()


def test_config_toml_can_enable_it(tmp_path):
    ns = {"QUANT_ROUTES": {}, "ALLOW_UNVALIDATED_LIVE": False}
    p = tmp_path / "config.toml"
    p.write_text("allow_unvalidated_live = true\n", encoding="utf-8")
    assert user_config.apply(ns, str(p)) == [] and ns["ALLOW_UNVALIDATED_LIVE"] is True


def test_telemetry_flags_validated_routes(monkeypatch):
    monkeypatch.setattr(telemetry, "account_snapshot", lambda: None)
    monkeypatch.setattr(telemetry, "bot_positions", lambda symbol=None: [])
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda *a: [], raising=False)
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: None)
    monkeypatch.setattr(telemetry, "route_risk", lambda *a: (0.2, 0.3))
    quant = telemetry.symbol_telemetry("HK50", "H4", None)
    classic = telemetry.symbol_telemetry("EURUSD", "H1", None)
    assert quant["validated"] and quant["live_allowed"]
    assert not classic["validated"] and not classic["live_allowed"]
