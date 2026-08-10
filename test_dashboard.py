import pytest
import config
import dashboard
import json
import urllib.parse

def test_page_config_html_rendering():
    """Garante que _page_config renderiza o formulario HTML com todos os cartoes de configuracao."""
    html = dashboard._page_config()
    assert "<!DOCTYPE html>" in html
    assert "Configuracao" in html
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
    assert "Relatorio de Performance" in html

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
    
    def dummy_send_response(code): handler.last_code = code
    def dummy_send_header(k, v): pass
    def dummy_end_headers(): pass
    
    handler.send_response = dummy_send_response
    handler.send_header = dummy_send_header
    handler.end_headers = dummy_end_headers
    
    handler.do_GET()
    assert handler.last_code == 200
    assert b"Configuracao" in handler.wfile.data
