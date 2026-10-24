"""bot.bat config: precisa mostrar as rotas quant e as travas reais de risco."""
import importlib
import os
import sys

from mt5bot.core import config

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))


def test_show_config_lists_quant_routes_and_real_risk_key(monkeypatch, capsys):
    show_config = importlib.import_module("show_config")
    monkeypatch.setattr(show_config, "_balance", lambda: 16.26)
    monkeypatch.setattr(config, "MAX_RISK_PER_TRADE_PERCENT", 0.7)

    show_config.run_show_config()
    out = capsys.readouterr().out

    assert "Risco por Trade: 0.7%" in out
    assert "HK50   H4  PULLB" in out and "US500  D1  RSI2MR" in out
    assert "= $0.33 com saldo $16.26" in out
    assert "limite proprio: 12.0% do saldo = $1.95" in out
