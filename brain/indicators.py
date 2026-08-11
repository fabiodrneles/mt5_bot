import pandas as pd
import numpy as np

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula a Media Movel Exponencial."""
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcula a Media Movel Simples."""
    return series.rolling(window=period).mean()

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Calcula as Bandas de Bollinger (SMA, Upper, Lower)."""
    sma = calculate_sma(series, period)
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return sma, upper, lower

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcula o Average True Range (ATR) para medicao de risco dinamico."""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    # Welles Wilder's Smoothing for ATR
    atr = np.zeros(len(df))
    if len(df) < period:
        return pd.Series(atr, index=df.index)
        
    atr[period-1] = true_range[0:period].mean()
    for i in range(period, len(df)):
        atr[i] = (atr[i-1] * (period - 1) + true_range.iloc[i]) / period
        
    return pd.Series(atr, index=df.index)

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona todas as metricas matematicas (EMAs, SMAs, Bollinger)
    necessarias para a Matriz de Setups do Palex.
    O DataFrame precisa ter 'close', 'high', 'low', 'open'.
    """
    if len(df) == 0:
        return df

    # Tendencias curtas e longas
    df['ema9'] = calculate_ema(df['close'], 9)
    df['sma21'] = calculate_sma(df['close'], 21)
    df['sma200'] = calculate_sma(df['close'], 200)
    
    # Direcao da EMA9 (Up/Down) para facilitar os gatilhos
    df['ema9_up'] = df['ema9'] > df['ema9'].shift(1)
    df['ema9_down'] = df['ema9'] < df['ema9'].shift(1)
    
    # Direcao da SMA21
    df['sma21_up'] = df['sma21'] > df['sma21'].shift(1)
    df['sma21_down'] = df['sma21'] < df['sma21'].shift(1)

    # Volatilidade (Bandas de Bollinger e ATR)
    sma20, upper, lower = calculate_bollinger_bands(df['close'], 20, 2.0)
    df['bollinger_mid'] = sma20
    df['bollinger_upper'] = upper
    df['bollinger_lower'] = lower
    df['atr'] = calculate_atr(df, 14)
    
    return df
