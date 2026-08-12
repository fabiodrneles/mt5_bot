import pytest
from mt5bot.core import config
from interfaces import dashboard
import json
import urllib.parse

def test_page_config_html_rendering():
    """Garante que _page_config renderiza o formulario HTML com todos os cartoes de configuracao."""
    html = dashboard._page_config()
    assert "<!DOCTYPE html>" in html
    assert "Configuração" in html  # MT5Bot — Configuração (title)
    assert "Proteção de Capital & Escudo de Risco" in html
    assert "Setup 9.3 (Larry Williams)" in html
    assert "Filtro MTF (Timeframe Maior)" in html
    assert "Filtro de Volume (RVOL)" in html
    assert "max_risk_pct" in html
    assert "max_daily_loss_pct" in html

def test_page_report_html_rendering():
    """Garante que _page_report renderiza o relatorio HTML sem erros."""
    html = dashboard._page_report()
    assert "<!DOCTYPE html>" in html
    assert "RELATÓRIO DE PERFORMANCE" in html

def test_apply_config_updates_global_config(monkeypatch):
    """Valida se _apply_config atualiza corretamente as variaveis em config.py isoladamente."""
    # Preservar atributos originais do config
    for k in ["SYMBOLS", "VOLUME_INITIAL", "EMA_PERIOD", "EMA_FILTER_PERIOD",
              "SETUP_93_ENABLED", "MTF_FILTER_ENABLED", "RVOL_FILTER_ENABLED",
              "RVOL_THRESHOLD", "MAX_RISK_PER_TRADE_PERCENT", "ABSOLUTE_MAX_TRADE_RISK_PERCENT",
              "MAX_DAILY_LOSS_PERCENT", "MAX_SPREAD_POINTS", "TRADING_START_TIME", "TIMEFRAME_NAME"]:
        monkeypatch.setattr(config, k, getattr(config, k))


    data = {
        "symbols": "EURUSD, GBPUSD, WING24",
        "volume": 0.05,
        "ema_period": 12,
        "ema_filter": 26,
        "setup_92": True,
        "setup_93": True,
        "mtf_filter": True,
        "rvol_filter": True,
        "rvol_threshold": 1.25,
        "rvol_lookback": 25,
        "flat_filter": True,
        "flat_threshold": 8,
        "max_risk_pct": 1.2,
        "abs_max_risk_pct": 2.0,
        "max_daily_loss_pct": 3.0,
        "max_spread": 40,
        "enable_breakeven": True,
        "trading_hours_enabled": True,
        "trading_start_time": "09:30",
        "trading_end_time": "16:30",
        "partial_exit": True,
        "partial_pct": 0.6,
        "partial_target": 1.2,
        "adaptive_target": True,
        "atr_threshold": 1.8,
        "tick_offset": 2,
        "scan_interval": 15,
        "retry_interval": 45,
        "rates_count": 150,
        "timeframe": "M15",
    }
    
    dashboard._apply_config(data)
    
    assert config.SYMBOLS == ["EURUSD", "GBPUSD", "WING24"]
    assert config.VOLUME_INITIAL == 0.05
    assert config.EMA_PERIOD == 12
    assert config.EMA_FILTER_PERIOD == 26
    assert config.SETUP_93_ENABLED is True
    assert config.MTF_FILTER_ENABLED is True
    assert config.RVOL_FILTER_ENABLED is True
    assert config.RVOL_THRESHOLD == 1.25
    assert config.MAX_RISK_PER_TRADE_PERCENT == 1.2
    assert config.MAX_DAILY_LOSS_PERCENT == 3.0
    assert config.MAX_SPREAD_POINTS == 40
    assert config.TRADING_START_TIME == "09:30"
    assert config.TIMEFRAME_NAME == "M15"


def test_dashboard_handler_get_requests(monkeypatch):
    """Testa manipulador de requisições GET do HTTP server."""
    class DummyWfile:
        def __init__(self):
            self.data = b""
        def write(self, b):
            self.data += b

    handler = dashboard._DashboardHandler.__new__(dashboard._DashboardHandler)
    handler.path = "/config"
    handler.wfile = DummyWfile()
    handler.headers = _FakeHeaders(0)  # Set headers so _lang_from_cookie works
    handler.send_response = lambda code: setattr(handler, "last_code", code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None

    handler.do_GET()
    assert handler.last_code == 200
    assert "Configuração" in handler.wfile.data.decode("utf-8")  # Title contains "Configuração" (pt)


class _FakeHeaders:
    def __init__(self, length=0):
        self.length = length
    def get(self, key, default=None):
        return self.length if key == "Content-Length" else default


class _FakeRfile:
    def __init__(self, body=b""):
        self.body = body
    def read(self, n):
        return self.body


def _make_handler(monkeypatch, path="/config", body=b"", content_length=0):
    handler = dashboard._DashboardHandler.__new__(dashboard._DashboardHandler)
    handler.path = path
    handler.wfile = _FakeWfile()
    handler.headers = _FakeHeaders(content_length)
    handler.rfile = _FakeRfile(body)
    handler.last_code = None
    handler.send_response = lambda code: setattr(handler, "last_code", code)
    handler.send_header = lambda k, v: None
    handler.end_headers = lambda: None
    return handler


class _FakeWfile:
    def __init__(self):
        self.data = b""
    def write(self, b):
        self.data += b


def test_find_free_port_retorna_porta(monkeypatch):
    port = dashboard._find_free_port(start=18000, attempts=3)
    assert 18000 <= port < 18003


def test_find_free_port_fallback_quando_sem_porta_livre(monkeypatch):
    import socket
    class _Bound:
        def __enter__(self):
            raise OSError("porta ocupada")
        def __exit__(self, *a):
            return False
    monkeypatch.setattr(socket, "socket", lambda *a, **k: _Bound())
    assert dashboard._find_free_port(start=18010, attempts=5) == 18010


def test_page_config_saved_render(monkeypatch):
    html = dashboard._page_config_saved()
    assert "CONFIGURAÇÃO APLICADA" in html
    assert "<!DOCTYPE html>" in html


def test_page_report_com_dados(monkeypatch, tmp_path):
    from mt5bot.data import tracker as tracker_mod
    trades = [
        {"id": 1, "symbol": "WIN", "side": "BUY", "setup": "9.1", "result": "win",
         "entry_price": 100.0, "exit_price": 102.0, "pnl_pips": 10.0,
         "pnl_money": 10.0, "entry_time": "2026-08-01T10:00:00"},
        {"id": 2, "symbol": "HK50", "side": "SELL", "setup": "PC", "result": "loss",
         "entry_price": 50.0, "exit_price": 51.0, "pnl_pips": -5.0,
         "pnl_money": -5.0, "entry_time": "2026-08-01T12:00:00"},
    ]
    trades_file = tmp_path / "trades.json"
    import json as _json
    trades_file.write_text(_json.dumps(trades), encoding="utf-8")
    monkeypatch.setattr(tracker_mod, "_TRADES_FILE", str(trades_file))

    html = dashboard._page_report()
    assert "WIN" in html
    assert "HK50" in html
    assert "9.1" in html
    assert "PC" in html
    assert "1/0" in html
    assert "0/1" in html
    assert "HK50" in html


def test_page_report_vazio(monkeypatch, tmp_path):
    from mt5bot.data import tracker as tracker_mod
    trades_file = tmp_path / "trades.json"
    trades_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(tracker_mod, "_TRADES_FILE", str(trades_file))
    html = dashboard._page_report()
    assert "Nenhuma operação registrada ainda" in html
    assert "Nenhum dado ainda" in html


def test_handler_get_report_e_api_e_404(monkeypatch, tmp_path):
    from mt5bot.data import tracker as tracker_mod
    import json as _json
    trades_file = tmp_path / "trades.json"
    trades_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(tracker_mod, "_TRADES_FILE", str(trades_file))

    h = _make_handler(monkeypatch, path="/report")
    h.do_GET()
    assert h.last_code == 200
    assert "RELATÓRIO DE PERFORMANCE" in h.wfile.data.decode("utf-8")

    h = _make_handler(monkeypatch, path="/api/summary")
    h.do_GET()
    assert h.last_code == 200
    payload = json.loads(h.wfile.data)
    assert payload["total_trades"] == 0

    h = _make_handler(monkeypatch, path="/nada")
    h.do_GET()
    assert h.last_code == 404


def test_handler_post_config_save(monkeypatch):
    body = (
        "symbols=EURUSD%2C+GBPUSD&volume=0.05&ema_period=12&ema_filter=26"
        "&setup_92=1&setup_93=1&mtf_filter=1&rvol_filter=1&rvol_threshold=1.25"
        "&rvol_lookback=25&flat_filter=1&flat_threshold=8&max_risk_pct=1.2"
        "&abs_max_risk_pct=2.0&max_daily_loss_pct=3.0&max_spread=40"
        "&enable_breakeven=1&trading_hours_enabled=1&trading_start_time=09%3A30"
        "&trading_end_time=16%3A30&partial_exit=1&partial_pct=0.6&partial_target=1.2"
        "&adaptive_target=1&atr_threshold=1.8&tick_offset=2&scan_interval=15"
        "&retry_interval=45&rates_count=150&timeframe=M15"
    ).encode("utf-8")
    h = _make_handler(monkeypatch, path="/config/save", body=body, content_length=len(body))
    h.do_POST()
    assert h.last_code == 200
    assert b"CONFIGURA" in h.wfile.data
    assert dashboard._config_ready.is_set()
    assert config.SYMBOLS == ["EURUSD", "GBPUSD"]
    assert config.TIMEFRAME_NAME == "M15"


def test_handler_post_config_save_invalido_usa_defaults(monkeypatch):
    monkeypatch.setattr(config, "VOLUME_INITIAL", 0.01)
    monkeypatch.setattr(config, "EMA_PERIOD", 9)
    body = "volume=abc&ema_period=xyz".encode("utf-8")
    h = _make_handler(monkeypatch, path="/config/save", body=body, content_length=len(body))
    h.do_POST()
    assert h.last_code == 200
    assert config.VOLUME_INITIAL == 0.01
    assert config.EMA_PERIOD == 9


def test_handler_post_404(monkeypatch):
    h = _make_handler(monkeypatch, path="/outro", body=b"", content_length=0)
    h.do_POST()
    assert h.last_code == 404


def test_log_message_silencioso(monkeypatch):
    h = dashboard._DashboardHandler.__new__(dashboard._DashboardHandler)
    import io
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    h.log_message("linha %s", "x")
    assert captured.getvalue() == ""


def test_open_config_aguarda_evento(monkeypatch):
    class FakeEvent:
        def clear(self):
            pass
        def wait(self, timeout=None):
            return True
    monkeypatch.setattr(dashboard, "_config_ready", FakeEvent())
    monkeypatch.setattr(dashboard.webbrowser, "open", lambda url: True)
    assert dashboard.open_config() is True


def test_open_report_com_input(monkeypatch):
    class FakeEvent:
        def clear(self):
            pass
        def wait(self, timeout=None):
            return True
    monkeypatch.setattr(dashboard, "_config_ready", FakeEvent())
    monkeypatch.setattr(dashboard.webbrowser, "open", lambda url: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    dashboard.open_report()
    assert True
