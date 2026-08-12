import pytest
from mt5bot.core import config
from mt5bot.risk import risk_calculator
from mt5bot.execution import executor
from mt5bot.data import tracker

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
    assert risk_calculator.is_within_trading_hours(current_time_str="10:00", start_str="09:15", end_str="16:45") is True
    assert risk_calculator.is_within_trading_hours(current_time_str="08:30", start_str="09:15", end_str="16:45") is False
    assert risk_calculator.is_within_trading_hours(current_time_str="17:00", start_str="09:15", end_str="16:45") is False

def test_is_within_trading_hours_hk50_and_symbol_specific(monkeypatch):
    """Valida janela de horario especifica para HK50 (sessao noturna 22:15-12:00 BRT) e WIN."""
    monkeypatch.undo()
    # HK50 (22:15 as 12:00 BRT do dia seguinte)
    assert risk_calculator.is_within_trading_hours(symbol="HK50", current_time_str="23:00") is True
    assert risk_calculator.is_within_trading_hours(symbol="HK50", current_time_str="08:00") is True
    assert risk_calculator.is_within_trading_hours(symbol="HK50", current_time_str="15:00") is False

    # WIN (Mini Indice 09:15 as 17:15 BRT)
    assert risk_calculator.is_within_trading_hours(symbol="WING24", current_time_str="11:30") is True
    assert risk_calculator.is_within_trading_hours(symbol="WING24", current_time_str="20:00") is False


def test_open_market_suggestions_and_margin(monkeypatch):
    """Testa a identificacao de todos os ativos fechados e geracao de sugestoes com calculo de margem."""
    monkeypatch.undo()
    # Simula todos os ativos do usuario fechados
    monkeypatch.setattr(risk_calculator, "is_within_trading_hours", lambda sym=None, **k: False if sym in ["WIN", "WDO"] else True)
    
    all_closed = risk_calculator.check_all_symbols_closed(["WIN", "WDO"])
    assert all_closed is True

    sugg_data = risk_calculator.get_open_market_suggestions(["WIN", "WDO"])
    assert sugg_data["all_closed"] is True
    assert len(sugg_data["suggestions"]) > 0
    first = sugg_data["suggestions"][0]
    assert "margin" in first
    assert "currency" in first
    assert first["margin"] > 0



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
    """Daily Max Loss Shield: o execution_manager bloqueia novas ordens quando a perda diaria atinge o limite."""
    import MetaTrader5 as mt5
    from mt5bot.execution import execution_manager

    # Cenário: sem posições/ordens (scan de novos setups)
    monkeypatch.setattr(mt5, "positions_get", lambda symbol=None: [])
    monkeypatch.setattr(mt5, "orders_get", lambda symbol=None: [])

    # Perda diaria acima do limite de 2% de R$ 10.000 (R$ 200)
    monkeypatch.setattr(tracker, "get_daily_pnl", lambda target_date=None: -250.0)
    monkeypatch.setattr(risk_calculator, "get_trading_session_info", lambda symbol=None: {"is_open": True})
    from unittest.mock import Mock
    place_mock = Mock(return_value=None)
    monkeypatch.setattr(executor, "place_buy_stop", place_mock)

    # Setup válido (9.1 de compra) para garantir que a única barreira é o shield
    df = _make_scannable_df(ema_down_prev=True)
    execution_manager.manage_cycle("EURUSD", df)

    # Não deve ter chamado place_buy_stop
    place_mock.assert_not_called()


def _make_scannable_df(ema_down_prev=False):
    """Monta um DataFrame mínimo com indicadores para o StrategyScorer (setup 9.1 de compra)."""
    import pandas as pd
    data = {
        'time': pd.date_range("2023-01-01", periods=5, freq='h'),
        'open': [10, 9, 8, 7, 8],
        'high': [11, 10, 9, 8, 10],
        'low': [9, 8, 7, 6, 7],
        'close': [9, 8, 7, 6, 9],
    }
    df = pd.DataFrame(data)
    df['ema9_down'] = [True, True, True, True, False]
    df['ema9_up'] = [False, False, False, False, True]
    df['sma21_up'] = False
    df['sma21_down'] = True
    df['sma21'] = 15.0
    df['sma200'] = 5.0
    df['bollinger_lower'] = 4.0
    df['bollinger_upper'] = 20.0
    df['atr'] = 1.0
    return df
