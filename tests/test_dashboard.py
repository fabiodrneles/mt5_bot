"""Dashboard web ao vivo (interfaces/dashboard.py)."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from interfaces import dashboard
from mt5bot.core import config, telemetry
from mt5bot.data import tracker


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.fixture
def live_env(monkeypatch):
    monkeypatch.setattr(dashboard, "_ensure_mt5", lambda: True)
    monkeypatch.setattr(telemetry, "account_snapshot", lambda: {
        "login": 1, "real": True, "balance": 16.26, "equity": 16.38, "margin_free": 14.2, "currency": "USD"})
    monkeypatch.setattr(telemetry, "bot_positions", lambda symbol=None: [
        {"ticket": 9, "symbol": "HK50", "side": "BUY", "volume": 0.01, "open": 23050.0, "sl": 22850.0,
         "tp": 23450.0, "profit": 0.12, "setup": "PULLB"}])
    monkeypatch.setattr(dashboard, "_route_rows", lambda balance: [
        {"symbol": "HK50", "tf": "H4", "setup": "PULLB", "risk": 0.21, "limit": 0.33, "next_close": "em 1h 05m"}])
    monkeypatch.setattr(tracker, "get_daily_pnl", lambda target_date=None: 0.12)
    trades = [
        {"result": "loss", "pnl_money": -0.2, "setup": "PULLB", "symbol": "HK50", "side": "BUY",
         "exit_time": "2026-10-26T03:00:00"},
        {"result": "win", "pnl_money": 0.4, "setup": "PULLB", "symbol": "HK50", "side": "SELL",
         "exit_time": "2026-10-25T03:00:00"},
        {"result": "open", "pnl_money": None, "setup": "PULLB", "symbol": "HK50"},
    ]
    monkeypatch.setattr(tracker, "get_all_trades", lambda: trades)


def test_live_snapshot_has_account_routes_positions_and_chronological_stats(live_env):
    snap = dashboard.live_snapshot()
    assert snap["mt5_ok"] and snap["account"]["balance"] == 16.26 and snap["today"] == 0.12
    assert snap["routes"][0]["risk"] == 0.21 and snap["positions"][0]["profit"] == 0.12
    assert snap["stats"]["trades"] == 2 and snap["stats"]["net"] == 0.2
    # curva em ordem de saida: +0.40 (dia 25) e depois -0.20 (dia 26)
    assert [c["equity"] for c in snap["stats"]["curve"]] == [0.4, 0.2]
    assert snap["history"][0]["time"] == "2026-10-26 03:00"  # mais recente primeiro
    assert snap["by_setup"]["PULLB"]["trades"] == 2


def test_live_snapshot_without_mt5_still_serves_history(live_env, monkeypatch):
    monkeypatch.setattr(dashboard, "_ensure_mt5", lambda: False)
    snap = dashboard.live_snapshot()
    assert snap["mt5_ok"] is False and snap["account"] is None and snap["stats"]["trades"] == 2


@pytest.mark.parametrize("lang,word", [("pt", "Patrimônio"), ("en", "Equity"), ("es", "Patrimonio")])
def test_live_page_is_localized_and_polls_api(lang, word):
    page = dashboard.page_live(lang)
    assert word in page and "/api/live" in page and "setInterval(tick" in page and 'lang="%s"' % lang in page


def test_config_page_shows_quant_routes_and_own_risk_limit():
    page = dashboard.page_config("pt")
    for sym, route in config.QUANT_ROUTES.items():
        assert sym in page and route["setup"] in page
    assert "limite próprio" in page and "somente leitura" in page


def test_config_page_escapes_html(monkeypatch):
    monkeypatch.setattr(config, "ASSET_SETUPS", {"<img src=x onerror=alert(1)>": ["x"]})
    page = dashboard.page_config("pt")
    assert "&lt;img src=x onerror=alert(1)&gt;" in page and "<img src=x" not in page


def test_http_server_routes_and_language_cookie(live_env):
    server, url = dashboard.serve(open_browser=False, port=dashboard._find_free_port(18600))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        live = json.loads(urllib.request.urlopen(url + "api/live").read())
        assert live["account"]["real"] is True
        req = urllib.request.Request(url, headers={"Cookie": "lang=en"})
        assert "Bot positions" in urllib.request.urlopen(req).read().decode("utf-8")
        assert urllib.request.urlopen(url + "config").status == 200
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "nao-existe")
    finally:
        server.shutdown()
        server.server_close()


def test_clean_lang_fallback():
    assert dashboard._clean_lang("xx") == "pt" and dashboard._clean_lang("es") == "es"
