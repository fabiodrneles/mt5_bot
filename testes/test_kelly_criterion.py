import pytest
from mt5bot.risk.risk_calculator import calculate_dynamic_kelly_risk
from mt5bot.core import config

def test_kelly_high_prob():
    # Win Prob: 80%, RRR = 1.5
    risk = calculate_dynamic_kelly_risk(0.80, 1.5)
    assert risk == 2.0

def test_kelly_low_prob():
    risk_low = calculate_dynamic_kelly_risk(0.40, 1.5)
    # 0.0 Half kelly, clamped to 0.5% (minimum)
    assert risk_low == 0.5

def test_kelly_medium_prob():
    risk = calculate_dynamic_kelly_risk(0.412, 1.5)
    assert abs(risk - 1.0) < 0.1 # Should be around 1%

def test_kelly_fallback():
    # Prob > 1.0 or RRR <= 0
    risk = calculate_dynamic_kelly_risk(1.2, 1.5)
    assert risk == config.MAX_RISK_PER_TRADE_PERCENT
