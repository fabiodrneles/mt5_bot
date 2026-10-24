"""Assistente de primeiro uso e trava de conta REAL (spec 006)."""
import importlib
import os
import sys

import MetaTrader5 as mt5

from mt5bot.core import config, user_config
from mt5bot.execution import quant_manager

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
wizard = importlib.import_module("setup_wizard")


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _mt5(monkeypatch, connected=True, real=True, algo=True):
    monkeypatch.setattr(mt5, "initialize", lambda *a, **k: connected)
    monkeypatch.setattr(mt5, "terminal_info", lambda: _Obj(trade_allowed=algo), raising=False)
    monkeypatch.setattr(mt5, "account_info", lambda: _Obj(login=1, trade_mode=2 if real else 0, balance=16.26,
                                                          equity=16.0, margin_free=14.0, currency="USD"))
    monkeypatch.setattr(mt5, "symbol_select", lambda s, e: True)
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda *a: None)


def test_without_mt5_explains_and_does_not_hang(monkeypatch, capsys):  # AC-1
    _mt5(monkeypatch, connected=False)
    assert wizard.main(ask=lambda _: "x") == 1
    assert "Abra o terminal" in capsys.readouterr().out


def test_algo_trading_off_is_reported(monkeypatch):
    _mt5(monkeypatch, algo=False)
    report = wizard.check_environment()
    assert any("Algo Trading" in p for p in report["problems"])


def test_real_account_needs_explicit_word(monkeypatch, tmp_path):  # FR-2
    _mt5(monkeypatch, real=True)
    target = tmp_path / "config.toml"
    monkeypatch.setattr(user_config.paths, "config_file", lambda: str(target))
    monkeypatch.setattr(config, "LIVE_CONFIRMED", False)
    monkeypatch.setattr(sys, "stdin", _Obj(isatty=lambda: True))
    assert wizard.main(ask=lambda _: "sim") == 2 and not target.exists()       # "sim" nao basta
    assert wizard.main(ask=lambda _: "confirmo") == 0
    assert "live_confirmed = true" in target.read_text(encoding="utf-8")


def test_demo_account_needs_no_confirmation(monkeypatch):
    _mt5(monkeypatch, real=False)
    assert wizard.main(ask=lambda _: (_ for _ in ()).throw(AssertionError("nao deveria perguntar"))) == 0


def test_set_value_replaces_commented_line_and_keeps_rest(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("# topo\n# live_confirmed = false\n[routes.US500]\nmax_risk_pct = 5\n", encoding="utf-8")
    user_config.set_value("live_confirmed", True, str(p))
    text = p.read_text(encoding="utf-8")
    assert text == "# topo\nlive_confirmed = true\n[routes.US500]\nmax_risk_pct = 5\n"
    ns = {"QUANT_ROUTES": {"US500": {"timeframe": "D1", "setup": "RSI2MR"}}}
    assert user_config.apply(ns, str(p)) == [] and ns["LIVE_CONFIRMED"] is True


def test_set_value_inserts_before_route_sections(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[routes.US500]\nmax_risk_pct = 5\n", encoding="utf-8")
    user_config.set_value("live_confirmed", True, str(p))
    assert p.read_text(encoding="utf-8").startswith("live_confirmed = true\n[routes.US500]")


def test_unconfirmed_real_account_blocks_new_quant_entries(monkeypatch):  # AC-2
    monkeypatch.setattr(mt5, "account_info", lambda: _Obj(trade_mode=2, balance=16.26, margin_free=14.0))
    monkeypatch.setattr(config, "LIVE_CONFIRMED", False)
    assert quant_manager.real_account_unconfirmed() is True
    monkeypatch.setattr(config, "LIVE_CONFIRMED", True)
    assert quant_manager.real_account_unconfirmed() is False
    monkeypatch.setattr(config, "LIVE_CONFIRMED", False)
    monkeypatch.setattr(mt5, "account_info", lambda: _Obj(trade_mode=0))
    assert quant_manager.real_account_unconfirmed() is False      # DEMO opera


def test_closed_input_never_confirms(monkeypatch, tmp_path):
    """stdin fechado (EOF) ou Ctrl+C: nao quebra e nao libera."""
    _mt5(monkeypatch, real=True)
    target = tmp_path / "config.toml"
    monkeypatch.setattr(user_config.paths, "config_file", lambda: str(target))
    monkeypatch.setattr(config, "LIVE_CONFIRMED", False)
    monkeypatch.setattr(sys, "stdin", _Obj(isatty=lambda: True))

    def eof(_):
        raise EOFError

    assert wizard.main(ask=eof) == 2 and not target.exists()
