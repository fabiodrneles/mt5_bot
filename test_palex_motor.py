import pytest
import pandas as pd
import numpy as np
import sys
import os

# Nao inserimos no path para nao conflitar com modulos raiz. Vamos importar como modulo.
from brain.indicators import add_all_indicators
from brain.setups import PalexScorer

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
    
    # Preencher outras colunas necessarias pelo PalexScorer para evitar KeyErrors
    df['sma21_up'] = False
    df['sma21_down'] = True
    df['sma21'] = 15.0
    df['sma200'] = 5.0 # Preço (9) > 5.0 -> permite compra
    df['bollinger_lower'] = 4.0
    df['bollinger_upper'] = 20.0
    df['atr'] = 1.0

    valid_setups, _ = PalexScorer.evaluate_all(df)
    
    # Deve encontrar o Setup 9.1 de compra
    assert len(valid_setups) > 0, "Deveria ter encontrado um setup"
    best = valid_setups[0]
    assert best['setup'] == '9.1'
    assert best['action'] == 'buy'
    # Trigger deve ser a maxima do candle que fez virar (último candle) + 0.01
    assert best['trigger_price'] == 10.01

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

    valid_setups, _ = PalexScorer.evaluate_all(df)
    
    assert len(valid_setups) > 0
    best = valid_setups[0]
    assert best['setup'] == 'FFFD'
    assert best['action'] == 'buy'
    assert best['score'] == 35 # O FFFD eh o mais alto na nossa regra
