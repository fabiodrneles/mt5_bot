import pytest
import config
import risk_calculator
import strategy
import executor
import tracker

def test_get_account_balance_default(monkeypatch):
    """Retorna saldo padrao quando mt5.account_info() for None."""
    import MetaTrader5 as mt5
    monkeypatch.setattr(mt5, "account_info", lambda: None)
    balance = risk_calculator.get_account_balance()
    assert balance == config.DEFAULT_ACCOUNT_BALANCE

def test_get_account_balance_from_mt5(monkeypatch):
    """Retorna saldo da conta MT5 quando disponivel."""
    import MetaTrader5 as mt5
    class DummyAccountInfo:
        balance = 25000.0
    monkeypatch.setattr(mt5, "account_info", lambda: DummyAccountInfo())
    balance = risk_calculator.get_account_balance()
    assert balance == 25000.0

def test_calculate_risk_limits():
    """Verifica mapa de limites de risco para R$ 10.000 de saldo."""
    limits = risk_calculator.calculate_risk_limits(10000.0)
    assert limits["balance"] == 10000.0
    assert limits["max_trade_risk_currency"] == 100.0  # 1% de 10.000
    assert limits["absolute_max_trade_risk_currency"] == 150.0 # 1.5% de 10.000
    assert limits["max_daily_loss_currency"] == 200.0  # 2% de 10.000

def test_calculate_position_size_safe(monkeypatch):
    """Calcula lote seguro quando risco está dentro do limite de 1%."""
    import MetaTrader5 as mt5
    class DummySymbolInfo:
        trade_contract_size = 1.0
        trade_tick_size = 0.01
        trade_tick_value = 0.01
        volume_min = 0.01
        volume_max = 100.0
        volume_step = 0.01
    monkeypatch.setattr(mt5, "symbol_info", lambda sym: DummySymbolInfo())
    
    volume, risk_currency, is_safe, reason = risk_calculator.calculate_position_size(
        symbol="EURUSD",
        entry_price=100.00,
        sl_price=95.00,
        balance=10000.0
    )
    assert is_safe is True
    assert volume > 0
    assert risk_currency <= 150.0

def test_calculate_position_size_rejected_due_to_high_risk(monkeypatch):
    """Rejeita operacao se o lote minimo gerar risco > ABSOLUTE_MAX_TRADE_RISK_PERCENT (1.5%)."""
    import MetaTrader5 as mt5
    class DummySymbolInfo:
        trade_contract_size = 1.0
        trade_tick_size = 0.01
        trade_tick_value = 1.0
        volume_min = 1.0
        volume_max = 10.0
        volume_step = 1.0
    monkeypatch.setattr(mt5, "symbol_info", lambda sym: DummySymbolInfo())
    
    volume, risk_currency, is_safe, reason = risk_calculator.calculate_position_size(
        symbol="US500",
        entry_price=100.00,
        sl_price=98.00,
        balance=1000.0
    )
    assert is_safe is False
    assert "rejeitada" in reason.lower() or "excede" in reason.lower()

def test_is_within_trading_hours(monkeypatch):
    """Valida janela de horario de negociacao."""
    monkeypatch.undo()
    assert risk_calculator.is_within_trading_hours("10:00", "09:15", "16:45") is True
    assert risk_calculator.is_within_trading_hours("08:30", "09:15", "16:45") is False
    assert risk_calculator.is_within_trading_hours("17:00", "09:15", "16:45") is False

def test_spread_filter_rejection(monkeypatch):
    """Verifica se executor rejeita ordem quando spread excede MAX_SPREAD_POINTS."""
    import MetaTrader5 as mt5
    class DummyTick:
        ask = 100.10
        bid = 100.00  # Spread = 0.10 -> 1000 pips/pontos
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda sym: DummyTick())
    monkeypatch.setattr(executor, "get_symbol_info", lambda sym: type("DummyInfo", (), {"point": 0.0001, "trade_tick_size": 0.0001, "filling_mode": 1})())
    
    spread = executor.get_current_spread("EURUSD")
    assert spread == 1000
    
    # Ordem deve retornar None devido ao spread elevado
    result = executor.place_buy_stop("EURUSD", 100.50, 100.00)
    assert result is None

def test_daily_max_loss_shield(monkeypatch):
    """Verifica se novas ordens sao bloqueadas quando perda diaria atinge o limite."""
    monkeypatch.setattr(risk_calculator, "get_account_balance", lambda: 10000.0)
    monkeypatch.setattr(tracker, "get_daily_pnl", lambda: -250.0) # -R$ 250 > 2% de R$ 10.000 (R$ 200)
    monkeypatch.setattr(risk_calculator, "is_within_trading_hours", lambda: True)
    
    s_state = strategy.SymbolState("EURUSD")
    candle_ref = (1234567, 100.0, 105.0, 99.0, 104.0, 1000)
    
    # Nao deve criar ordem nem alterar estado
    strategy._place_entry_order(s_state, candle_ref, strategy.TradeSide.BUY, 0.01, None, [], "9.1")
    assert s_state.state == strategy.State.SCANNING
