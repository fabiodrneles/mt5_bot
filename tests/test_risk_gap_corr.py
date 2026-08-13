import pytest
from datetime import datetime, timedelta
import collections

# Para permitir o mock no risk_calculator
from mt5bot.risk import risk_calculator
import MetaTrader5 as mt5

class MockSymbolInfo:
    def __init__(self, name, point=0.00001):
        self.name = name
        self.point = point

class MockTick:
    def __init__(self, time):
        self.time = time

def test_check_correlation_risk():
    """Testa se o bloqueio de risco correlacionado funciona."""
    
    # Simula posições abertas
    PosMock = collections.namedtuple('PosMock', ['symbol'])
    open_positions = [PosMock(symbol="EURUSD"), PosMock(symbol="US30")]
    
    # 1. Tentar abrir GBPUSD (Correlacionado com EURUSD) -> Deve Bloquear
    is_safe, reason = risk_calculator.check_correlation_risk("GBPUSD", open_positions)
    assert is_safe is False
    assert "[CORRELATION RISK]" in reason
    
    # 2. Tentar abrir USDJPY (Correlacionado inversamente, mas no grupo 2) -> Deve Passar
    is_safe, reason = risk_calculator.check_correlation_risk("USDJPY", open_positions)
    assert is_safe is True
    
    # 3. Tentar abrir US500 (Correlacionado com US30) -> Deve Bloquear
    is_safe, reason = risk_calculator.check_correlation_risk("US500", open_positions)
    assert is_safe is False
    
    # 4. Tentar abrir HK50 (Nao esta nos grupos mapeados) -> Deve Passar
    is_safe, reason = risk_calculator.check_correlation_risk("HK50", open_positions)
    assert is_safe is True

def test_opening_gap_filter_safe(monkeypatch):
    """Testa cenário seguro (sem gap)."""
    
    # Mocks para MT5
    monkeypatch.setattr(mt5, "initialize", lambda: True)
    monkeypatch.setattr(mt5, "symbol_info", lambda s: MockSymbolInfo(s, point=1.0))
    
    now = datetime.now()
    # Vela 0 (Ontem) fechou no 100
    # Vela 1 (Hoje) abriu no 105
    mock_rates = [
        {'time': (now - timedelta(days=1)).timestamp(), 'open': 90, 'close': 100},
        {'time': now.timestamp(), 'open': 105, 'close': 106}
    ]
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda s, t, start, count: mock_rates)
    
    # Tick atual eh agora
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: MockTick(time=now.timestamp() + 60)) # +1 min
    
    # Gap eh de 5 (105 - 100), max_gap eh 50 -> DEVE PASSAR
    is_safe, reason = risk_calculator.opening_gap_filter("HK50", max_gap_pips=50.0, safe_minutes=5)
    assert is_safe is True
    assert "OK" in reason

def test_opening_gap_filter_blocked(monkeypatch):
    """Testa cenário de gap violento nos primeiros minutos."""
    
    monkeypatch.setattr(mt5, "initialize", lambda: True)
    monkeypatch.setattr(mt5, "symbol_info", lambda s: MockSymbolInfo(s, point=1.0))
    
    now = datetime.now()
    # Vela 0 fechou em 100, vela 1 abriu em 200 (Gap de 100 pontos)
    mock_rates = [
        {'time': (now - timedelta(days=1)).timestamp(), 'open': 90, 'close': 100},
        {'time': now.timestamp(), 'open': 200, 'close': 200}
    ]
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda s, t, start, count: mock_rates)
    
    # Tick atual eh agora + 2 minutos
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: MockTick(time=now.timestamp() + 120))
    
    # Limite é 50, Gap foi de 100 -> DEVE BLOQUEAR
    is_safe, reason = risk_calculator.opening_gap_filter("HK50", max_gap_pips=50.0, safe_minutes=5)
    assert is_safe is False
    assert "[GAP FILTER] Rejeitado" in reason

def test_opening_gap_filter_after_safe_window(monkeypatch):
    """Testa cenário de gap violento, mas já se passou muito tempo (fora da janela de perigo)."""
    
    monkeypatch.setattr(mt5, "initialize", lambda: True)
    monkeypatch.setattr(mt5, "symbol_info", lambda s: MockSymbolInfo(s, point=1.0))
    
    now = datetime.now()
    mock_rates = [
        {'time': (now - timedelta(days=1)).timestamp(), 'open': 90, 'close': 100},
        {'time': now.timestamp(), 'open': 200, 'close': 200} # Gap de 100
    ]
    monkeypatch.setattr(mt5, "copy_rates_from_pos", lambda s, t, start, count: mock_rates)
    
    # Tick atual eh agora + 30 minutos (safe window era 5 min)
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: MockTick(time=now.timestamp() + 1800))
    
    # Deve passar, pois o susto inicial do gap já diluiu no mercado
    is_safe, reason = risk_calculator.opening_gap_filter("HK50", max_gap_pips=50.0, safe_minutes=5)
    assert is_safe is True
    assert "OK" in reason
