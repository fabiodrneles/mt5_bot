import pytest
import pandas as pd
import numpy as np
import sys
import os

# Nao inserimos no path para nao conflitar com modulos raiz. Vamos importar como modulo.
from mt5bot.engine.indicators import add_all_indicators
from mt5bot.engine.strategy import StrategyScorer

TICK_SIZE = 0.05

def test_ema9_reversal_setup_91():
    """Testa se o motor reconhece um Setup 9.1 de Compra."""
    # Criamos um DataFrame fake simulando uma EMA9 caindo e depois virando pra cima
    # Precisamos de pelo menos 5 velas.
    data = {
        'time': pd.date_range("2023-01-01", periods=5, freq='h'),
        'open': [10, 9, 8, 7, 8],
        'high': [11, 10, 9, 8, 10],
        'low': [9, 8, 7, 6, 7],
        'close': [9, 8, 7, 6, 9]
    }
    df = pd.DataFrame(data)
    
    # Para forçar o EMA9 a se comportar rápido, vamos forçar os valores no mock,
    # ou deixar a funcao calcular, sabendo que com 5 periodos o EWMA pode demorar a reagir.
    # Vamos injetar manualmente as condicoes booleanas para testar isoladamente o `setups.py`
    df['ema9_down'] = [True, True, True, True, False]
    df['ema9_up'] = [False, False, False, False, True]
    
    # Preencher outras colunas necessarias pelo StrategyScorer para evitar KeyErrors
    df['sma21_up'] = False
    df['sma21_down'] = True
    df['sma21'] = 15.0
    df['sma200'] = 5.0 # Preço (9) > 5.0 -> permite compra
    df['bollinger_lower'] = 4.0
    df['bollinger_upper'] = 20.0
    df['atr'] = 1.0

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=TICK_SIZE)
    
    # Deve encontrar o Setup 9.1 de compra
    assert len(valid_setups) > 0, "Deveria ter encontrado um setup"
    best = valid_setups[0]
    assert best['setup'] == '9.1'
    assert best['action'] == 'buy'
    # Trigger deve ser a maxima do candle que fez virar (último candle) + 1 tick
    assert best['trigger_price'] == pytest.approx(10.0 + TICK_SIZE)

def test_bollinger_fffd():
    """Testa se o motor reconhece o setup Fechou Fora Fechou Dentro."""
    data = {
        'time': pd.date_range("2023-01-01", periods=5, freq='h'),
        'open': [10, 10, 10, 5, 8],
        'high': [11, 11, 11, 6, 9],
        'low': [9, 9, 9, 3, 7],
        'close': [10, 10, 10, 4, 8]  # Candle T-2 fecha em 4, T-1 fecha em 8
    }
    df = pd.DataFrame(data)
    
    df['ema9_down'] = False
    df['ema9_up'] = True
    df['sma21_up'] = True
    df['sma21_down'] = False
    df['sma21'] = 10.0
    df['sma200'] = 5.0
    df['atr'] = 1.0
    
    # Simulando banda inferior de bollinger em 5.0
    # No candle T-2 o close foi 4 (Fechou Fora da banda)
    # No candle T-1 o close foi 8 (Fechou Dentro da banda)
    df['bollinger_lower'] = [5.0, 5.0, 5.0, 5.0, 5.0]
    df['bollinger_upper'] = [15.0, 15.0, 15.0, 15.0, 15.0]

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=TICK_SIZE)
    
    assert len(valid_setups) > 0
    best = valid_setups[0]
    assert best['setup'] == 'FFFD'
    assert best['action'] == 'buy'
    assert best['score'] == 35 # O FFFD eh o mais alto na nossa regra


def test_russian_bb_buy_fires_with_bollinger_and_rsi14():
    """O setup russian_bb (HK50) deve disparar compra com bollinger_lower/rsi14
    e largura de banda >= RUSSIAN_BB_MIN_WIDTH (50.0 em preco), nao 50*tick_size."""
    data = {
        'time': pd.date_range("2023-01-01", periods=6, freq='h'),
        'open': [25000, 25020, 25040, 25010, 24980, 24960],
        'high': [25050, 25060, 25060, 25020, 24990, 24970],
        'low':  [24990, 25000, 25000, 24970, 24940, 24920],
        'close':[25010, 25030, 25020, 24980, 24950, 24930],
    }
    df = pd.DataFrame(data)
    df['sma21'] = 25000.0
    df['sma200'] = 24000.0  # abaixo do preco -> permite compra (filtro macro)
    df['ema9'] = 25010.0
    df['ema50'] = 25020.0   # ema9<sma21<ema50? nao: ema9<ema50 e sma21<ema50 -> sem downtrend
    df['bollinger_lower'] = 24955.0
    df['bollinger_upper'] = 25045.0   # bb_width = 90 >= 50
    df['rsi14'] = 25.0                # < RUSSIAN_BB_RSI_OVERSOLD (30)
    df['atr'] = 20.0
    df['ema9_up'] = False
    df['ema9_down'] = False
    df['sma21_up'] = False
    df['sma21_down'] = False

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, symbol="HK50")
    russian = [s for s in valid_setups if s['setup'] == 'russian_bb']
    assert len(russian) == 1, f"russian_bb deveria disparar, obtive: {[s['setup'] for s in valid_setups]}"
    assert russian[0]['action'] == 'buy'
    assert russian[0]['score'] == 100


def test_russian_bb_does_not_fire_when_width_below_minimum():
    """Largura de banda < 40.0 em preco nao deve gerar sinal russian_bb."""
    data = {
        'time': pd.date_range("2023-01-01", periods=6, freq='h'),
        'open': [25000, 25020, 25040, 25010, 24980, 24960],
        'high': [25050, 25060, 25060, 25020, 24990, 24970],
        'low':  [24990, 25000, 25000, 24970, 24940, 24920],
        'close':[25010, 25030, 25020, 24980, 24950, 24930],
    }
    df = pd.DataFrame(data)
    df['sma21'] = 25000.0
    df['sma200'] = 24000.0
    df['ema9'] = 25010.0
    df['ema50'] = 25020.0
    df['bollinger_lower'] = 24965.0
    df['bollinger_upper'] = 24995.0   # bb_width = 30 < 40
    df['rsi14'] = 25.0
    df['atr'] = 20.0
    df['ema9_up'] = False
    df['ema9_down'] = False
    df['sma21_up'] = False
    df['sma21_down'] = False

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, symbol="HK50")
    russian = [s for s in valid_setups if s['setup'] == 'russian_bb']
    assert len(russian) == 0


def test_russian_bb_eurusd_uses_asset_specific_min_width():
    """EURUSD usa RUSSIAN_BB_PARAMS (min_width 0.0008), nao o global (40.0).

    Uma banda de largura 0.0015 (>= 0.0008, mas << 40.0) deve disparar
    no EURUSD, mesmo estando abaixo do minimo global.
    """
    data = {
        'time': pd.date_range("2023-01-01", periods=6, freq='h'),
        'open': [1.0850, 1.0855, 1.0860, 1.0855, 1.0850, 1.0845],
        'high': [1.0860, 1.0870, 1.0865, 1.0860, 1.0855, 1.0848],
        'low':  [1.0845, 1.0850, 1.0855, 1.0850, 1.0842, 1.0828],
        'close':[1.0855, 1.0860, 1.0858, 1.0852, 1.0845, 1.0840],
    }
    df = pd.DataFrame(data)
    df['sma21'] = 1.0850
    df['sma200'] = 1.0800
    df['ema9'] = 1.0855
    df['ema50'] = 1.0845      # sem downtrend (ema9 > sma21 > ema50 = uptrend)
    df['bollinger_lower'] = 1.0830
    df['bollinger_upper'] = 1.0845    # bb_width = 0.0015 >= 0.0008 (EURUSD)
    df['rsi14'] = 20.0                # < rsi_oversold do EURUSD (35)
    df['atr'] = 0.0008
    df['ema9_up'] = False
    df['ema9_down'] = False
    df['sma21_up'] = False
    df['sma21_down'] = False

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.00001, symbol="EURUSD")
    russian = [s for s in valid_setups if s['setup'] == 'russian_bb']
    assert len(russian) == 1, f"russian_bb deveria disparar no EURUSD, obtive: {[s['setup'] for s in valid_setups]}"
    assert russian[0]['action'] == 'buy'


def test_russian_bb_eurusd_fallback_to_global_without_override():
    """Ativo SEM override no RUSSIAN_BB_PARAMS usa os valores globais.

    Um symbol arbitrario (ex: "XXXUSD") com banda largura 1.5 (>= 40? nao)
    NAO deve disparar, pois o minimo global (40.0) continua valido.
    """
    data = {
        'time': pd.date_range("2023-01-01", periods=6, freq='h'),
        'open': [25000, 25020, 25040, 25010, 24980, 24960],
        'high': [25050, 25060, 25060, 25020, 24990, 24970],
        'low':  [24990, 25000, 25000, 24970, 24940, 24920],
        'close':[25010, 25030, 25020, 24980, 24950, 24930],
    }
    df = pd.DataFrame(data)
    df['sma21'] = 25000.0
    df['sma200'] = 24000.0
    df['ema9'] = 25010.0
    df['ema50'] = 25020.0
    df['bollinger_lower'] = 24965.0
    df['bollinger_upper'] = 24980.0   # bb_width = 15 < 40
    df['rsi14'] = 25.0
    df['atr'] = 20.0
    df['ema9_up'] = False
    df['ema9_down'] = False
    df['sma21_up'] = False
    df['sma21_down'] = False

    valid_setups, _ = StrategyScorer.evaluate_all(df, tick_size=0.01, symbol="XXXUSD")
    russian = [s for s in valid_setups if s['setup'] == 'russian_bb']
    assert len(russian) == 0
