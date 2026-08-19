import pandas as pd
import numpy as np

def generate_vectorized_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera sinais vetorizados (1=Buy, -1=Sell, 0=Neutro) para todos os setups 
    suportados no mt5bot, traduzidos da lógica iterativa para vetorial (Pandas/NumPy).
    Assuma que o `df` já possui todos os indicadores calculados via `add_all_indicators`.
    """
    # ----------------------------------------------------
    # Preparação de máscaras auxiliares
    # ----------------------------------------------------
    shift_low1 = df['low'].shift(1)
    shift_high1 = df['high'].shift(1)
    shift_close1 = df['close'].shift(1)
    shift_close2 = df['close'].shift(2)
    shift_close3 = df['close'].shift(3)
    
    # ----------------------------------------------------
    # SETUP 9.1 (Reversão de Tendência Curta da EMA9)
    # ----------------------------------------------------
    # Buy: ema9_down anterior E ema9_up atual
    s91_buy = df['ema9_down'].shift(1) & df['ema9_up']
    # Sell: ema9_up anterior E ema9_down atual
    s91_sell = df['ema9_up'].shift(1) & df['ema9_down']
    
    df['signal_91'] = np.where(s91_buy, 1, np.where(s91_sell, -1, 0))

    # ----------------------------------------------------
    # SETUP 9.2 (Correção Leve contra a EMA9)
    # ----------------------------------------------------
    # Buy: ema9_up atual, ema9_up anterior, mínima do atual < mínima do anterior
    s92_buy = df['ema9_up'] & df['ema9_up'].shift(1) & (df['low'] < shift_low1)
    # Sell: ema9_down atual, ema9_down anterior, máxima do atual > máxima do anterior
    s92_sell = df['ema9_down'] & df['ema9_down'].shift(1) & (df['high'] > shift_high1)
    
    df['signal_92'] = np.where(s92_buy, 1, np.where(s92_sell, -1, 0))

    # ----------------------------------------------------
    # SETUP 9.3 (Correção Profunda com 2 fechamentos)
    # ----------------------------------------------------
    # Buy: ema9_up atual, ref (t-2) close < low(t-3), e c(t-1) < ref e c(t) < ref
    ref_buy_93 = df['close'].shift(2) < df['low'].shift(3)
    s93_buy = df['ema9_up'] & ref_buy_93 & (shift_close1 < df['close'].shift(2)) & (df['close'] < df['close'].shift(2))
    
    ref_sell_93 = df['close'].shift(2) > df['high'].shift(3)
    s93_sell = df['ema9_down'] & ref_sell_93 & (shift_close1 > df['close'].shift(2)) & (df['close'] > df['close'].shift(2))
    
    df['signal_93'] = np.where(s93_buy, 1, np.where(s93_sell, -1, 0))

    # ----------------------------------------------------
    # SETUP 9.4 (Falsa Reversão da EMA9)
    # ----------------------------------------------------
    # Buy: ema_up(t-2), ema_down(t-1), ema_up(t). E a low(t) >= low(t-1)
    s94_buy = df['ema9_up'].shift(2) & df['ema9_down'].shift(1) & df['ema9_up'] & (df['low'] >= shift_low1)
    # Sell: ema_down(t-2), ema_up(t-1), ema_down(t). E a high(t) <= high(t-1)
    s94_sell = df['ema9_down'].shift(2) & df['ema9_up'].shift(1) & df['ema9_down'] & (df['high'] <= shift_high1)
    
    df['signal_94'] = np.where(s94_buy, 1, np.where(s94_sell, -1, 0))
    
    # ----------------------------------------------------
    # PONTO CONTÍNUO (PC)
    # ----------------------------------------------------
    if 'sma21_up' in df.columns:
        s_pc_cond = df['sma21_up'] & df['sma21_up'].shift(1)
        dist_to_sma = df['low'] - df['sma21']
        s_pc_dist = (dist_to_sma >= 0) & (dist_to_sma <= (df['atr'] * 0.3))
        s_pc_buy = s_pc_cond & s_pc_dist
        df['signal_pc'] = np.where(s_pc_buy, 1, 0)
    else:
        df['signal_pc'] = 0

    # ----------------------------------------------------
    # FFFD (Fechou Fora, Fechou Dentro)
    # ----------------------------------------------------
    if 'bollinger_lower' in df.columns:
        # Buy: c(t-1) < bb_lower(t-1) AND c(t) > bb_lower(t)
        s_fffd_buy = (shift_close1 < df['bollinger_lower'].shift(1)) & (df['close'] > df['bollinger_lower'])
        # Sell: c(t-1) > bb_upper(t-1) AND c(t) < bb_upper(t)
        s_fffd_sell = (shift_close1 > df['bollinger_upper'].shift(1)) & (df['close'] < df['bollinger_upper'])
        df['signal_fffd'] = np.where(s_fffd_buy, 1, np.where(s_fffd_sell, -1, 0))
    else:
        df['signal_fffd'] = 0

    # ----------------------------------------------------
    # SETUP RUSSO (BB + RSI Mean Reversion)
    # ----------------------------------------------------
    if 'bollinger_lower' in df.columns and 'rsi14' in df.columns:
        min_width = 50.0  # Usando o default para vetorização rapida (pode ser ajustado)
        bb_width = df['bollinger_upper'] - df['bollinger_lower']
        width_ok = bb_width >= min_width
        
        uptrend = (df['ema9'] > df['sma21']) & (df['sma21'] > df['ema50'])
        downtrend = (df['ema9'] < df['sma21']) & (df['sma21'] < df['ema50'])
        
        s_russ_buy = (df['low'] < df['bollinger_lower']) & width_ok & (~downtrend) & (df['rsi14'] < 30)
        s_russ_sell = (df['high'] > df['bollinger_upper']) & width_ok & (~uptrend) & (df['rsi14'] > 70)
        
        df['signal_russian'] = np.where(s_russ_buy, 1, np.where(s_russ_sell, -1, 0))
    else:
        df['signal_russian'] = 0

    return df
