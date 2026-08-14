import logging
import pandas as pd
import numpy as np
from mt5bot.core import config

logger = logging.getLogger(__name__)

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula a Media Movel Exponencial."""
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcula a Media Movel Simples."""
    return series.rolling(window=period).mean()

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Calcula as Bandas de Bollinger e a largura da banda."""
    rm = df['close'].rolling(window=window).mean()
    rs = df['close'].rolling(window=window).std()
    df['bb_mid'] = rm
    df['bb_upper'] = rm + (rs * std)
    df['bb_lower'] = rm - (rs * std)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']
    return df



def calculate_rsi(series: pd.Series, period: int = 2) -> pd.Series:
    """Calcula o Indice de Forca Relativa (IFR/RSI) — Wilder."""
    if len(series) < period + 1:
        return pd.Series(np.nan, index=series.index)

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def calculate_sar(df: pd.DataFrame, af_step: float = 0.02, af_max: float = 0.20) -> pd.Series:
    """
    Calcula o SAR Parabolico (Wilder).
    Retorna uma Serie com o valor do SAR para cada candle.
    """
    if len(df) < 2:
        return pd.Series(np.nan, index=df.index)

    high = df['high'].to_numpy(dtype=float)
    low = df['low'].to_numpy(dtype=float)
    n = len(df)

    sar = np.full(n, np.nan)
    af = af_step
    is_bull = True
    ep = high[0]
    sar[0] = low[0]

    for i in range(1, n):
        prev_sar = sar[i - 1]
        if is_bull:
            prev_ep = ep
            if low[i] < prev_sar:
                is_bull = False
                sar[i] = prev_ep
                af = af_step
                ep = low[i]
            else:
                sar[i] = prev_sar + af * (prev_ep - prev_sar)
                if high[i] > prev_ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
                if low[i] < sar[i]:
                    is_bull = False
                    sar[i] = prev_ep
                    af = af_step
                    ep = low[i]
        else:
            prev_ep = ep
            if high[i] > prev_sar:
                is_bull = True
                sar[i] = prev_ep
                af = af_step
                ep = high[i]
            else:
                sar[i] = prev_sar + af * (prev_ep - prev_sar)
                if low[i] < prev_ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
                if high[i] > sar[i]:
                    is_bull = True
                    sar[i] = prev_ep
                    af = af_step
                    ep = high[i]

    # Alinhar primeiro ponto valido ao segundo candle (emulacao padrao)
    sar[0] = np.nan
    return pd.Series(sar, index=df.index)


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcula o ADX (Average Directional Index)."""
    if len(df) < period + 1:
        return pd.Series(np.nan, index=df.index)

    high = df['high']
    low = df['low']
    close = df['close']

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    return adx

def calculate_zscore(series: pd.Series, period: int = 21) -> pd.Series:
    """Calcula o Z-Score (Desvio em relação à media)."""
    mean = series.rolling(window=period).mean()
    std = series.rolling(window=period).std(ddof=0)
    # Evitar divisao por zero
    std = std.replace(0, np.nan)
    return (series - mean) / std


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona todas as metricas matematicas (EMAs, SMAs, Bollinger, IFR, SAR)
    necessarias para a Matriz de Setups.
    O DataFrame precisa ter 'close', 'high', 'low', 'open'.
    """
    if len(df) == 0:
        return df

    # Tendencias curtas e longas
    df['ema9'] = calculate_ema(df['close'], 9)
    df['sma21'] = calculate_sma(df['close'], 21)
    df['sma200'] = calculate_sma(df['close'], 200)

    # Medias auxiliares do livro (13, 28, 50)
    df['sma13'] = calculate_sma(df['close'], 13)
    df['sma28'] = calculate_sma(df['close'], 28)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['sma50'] = calculate_sma(df['close'], 50)

    # Media deslocada (DiNapoli): EMA12 deslocada 3 candles para tras
    df['ema12_displaced'] = calculate_ema(df['close'], 12).shift(3)

    # Osciladores (IFR curto e longo)
    df['rsi2'] = calculate_rsi(df['close'], 2)
    df['rsi9'] = calculate_rsi(df['close'], 9)
    df['rsi14'] = calculate_rsi(df['close'], period=14)

    # VWAP (ancorado por dia de negociacao, via 'time')
    df['vwap'] = calculate_vwap(df)

    # SAR Parabolico (0.02 / 0.20 — Wilder)
    df['sar'] = calculate_sar(df)
    
    # Direcao da EMA9 (Up/Down) para facilitar os gatilhos
    df['ema9_up'] = df['ema9'] > df['ema9'].shift(1)
    df['ema9_down'] = df['ema9'] < df['ema9'].shift(1)
    
    # Direcao da SMA21
    df['sma21_up'] = df['sma21'] > df['sma21'].shift(1)
    df['sma21_down'] = df['sma21'] < df['sma21'].shift(1)

    # Direcao da MME50
    df['ema50_up'] = df['ema50'] > df['ema50'].shift(1)
    df['ema50_down'] = df['ema50'] < df['ema50'].shift(1)

    # Volatilidade (Bandas de Bollinger e ATR)
    sma20, upper, lower = calculate_bollinger_bands(df['close'], 20, 2.0)
    df['bollinger_mid'] = sma20
    df['bollinger_upper'] = upper
    df['bollinger_lower'] = lower
    df['atr'] = calculate_atr(df, 14)
    
    # Machine Learning V2 Indicators
    df['adx'] = calculate_adx(df, period=14)
    df['z_score'] = calculate_zscore(df['close'], period=21)
    
    return df

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


def calculate_rvol(df: pd.DataFrame, lookback: int = None) -> tuple:
    """
    Calcula o RVOL (Volume Relativo) comparando o volume da vela atual com a media de N velas anteriores.
    Usa 'real_volume' quando disponivel (B3), senao 'tick_volume' (Forex).
    Retorna (rvol_ratio, current_vol, avg_vol).
    """
    if lookback is None:
        lookback = getattr(config, "RVOL_LOOKBACK", 20)

    if df is None or len(df) < lookback + 1:
        return (1.0, 0.0, 0.0)

    if 'real_volume' in df.columns and 'tick_volume' in df.columns:
        real = df['real_volume'].astype(float).fillna(0.0)
        tick = df['tick_volume'].astype(float).fillna(0.0)
        volumes = real.where(real > 0, tick)
    elif 'real_volume' in df.columns:
        volumes = df['real_volume'].astype(float).fillna(0.0)
    elif 'tick_volume' in df.columns:
        volumes = df['tick_volume'].astype(float).fillna(0.0)
    else:
        return (1.0, 0.0, 0.0)

    current_vol = float(volumes.iloc[-1])
    past_volumes = volumes.iloc[-lookback - 1:-1]
    avg_vol = float(past_volumes.mean()) if len(past_volumes) else 0.0

    if avg_vol <= 0:
        return (1.0, current_vol, 0.0)

    rvol_ratio = current_vol / avg_vol
    return (rvol_ratio, current_vol, avg_vol)


def check_mtf_trend(symbol: str, current_tf_name: str, side_name: str) -> bool:
    """
    Valida se a tendencia no timeframe superior (MTF) confirma a direcao da operacao.
    Compra: EMA9 do MTF acima da EMA21 e apontando para cima.
    Venda: EMA9 do MTF abaixo da EMA21 e apontando para baixo.
    Fallback permissivo (True) em caso de dados insuficientes ou erro,
    alinhado ao comportamento do modulo antigo.
    """
    import MetaTrader5 as mt5

    if not getattr(config, "MTF_FILTER_ENABLED", True):
        return True

    try:
        tf_map = getattr(config, "MTF_TIMEFRAME_MAP", {})
        mtf_tf_name = tf_map.get(current_tf_name, "H1")
        mtf_tf_const = config.AVAILABLE_TIMEFRAMES.get(mtf_tf_name, mt5.TIMEFRAME_H1)

        rates_count = getattr(config, "RATES_COUNT", 100)
        mtf_rates = mt5.copy_rates_from_pos(symbol, mtf_tf_const, 0, rates_count)

        if mtf_rates is None or len(mtf_rates) < 30:
            logger.warning(f"[{symbol}] Dados insuficientes para filtro MTF em {mtf_tf_name}.")
            return True

        mtf_df = pd.DataFrame(mtf_rates)
        if 'close' not in mtf_df.columns:
            mtf_df.columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'][:len(mtf_df.columns)]
        ema9_mtf = calculate_ema(mtf_df['close'], 9)
        ema21_mtf = calculate_ema(mtf_df['close'], 21)

        if ema9_mtf is None or ema21_mtf is None or len(ema9_mtf) < 2:
            return True

        last_ema9 = float(ema9_mtf.iloc[-1])
        last_ema21 = float(ema21_mtf.iloc[-1])

        if side_name == "BUY":
            return bool((last_ema9 >= last_ema21) and (ema9_mtf.iloc[-1] > ema9_mtf.iloc[-2]))
        else:
            return bool((last_ema9 <= last_ema21) and (ema9_mtf.iloc[-1] < ema9_mtf.iloc[-2]))

    except Exception as e:
        logger.error(f"Erro ao checar filtro MTF para {symbol}: {e}")
        return True


def check_rvol_filter(df: pd.DataFrame, side_name: str) -> bool:
    """
    Filtro de Volume Relativo: exige volume acima do limiar para confirmar o sinal.
    Fallback permissivo (True) quando o filtro esta desligado ou faltam dados.
    """
    if not getattr(config, "RVOL_FILTER_ENABLED", True):
        return True

    if df is None or len(df) < getattr(config, "RVOL_LOOKBACK", 20) + 1:
        return True

    rvol_ratio, _, _ = calculate_rvol(df)
    threshold = getattr(config, "RVOL_THRESHOLD", 1.15)
    return rvol_ratio >= threshold


def calculate_vwap(df: pd.DataFrame, period: int = 200) -> pd.Series:
    """
    Calcula o VWAP (Volume Weighted Average Price) ancorado por dia de negociacao.

    Preco tipico = (high + low + close) / 3; VWAP = cumsum(tp * vol) / cumsum(vol)
    dentro de cada sessao diaria (inferida pela coluna 'time', se presente;
    senao, rola pela janela `period` reutilizando 'real_volume'/'tick_volume').
    Fallback permissivo: Serie de NaN quando faltam dados de volume ou preco.
    """
    if df is None or len(df) == 0:
        return pd.Series(dtype=float)

    if not all(c in df.columns for c in ("high", "low", "close")):
        return pd.Series(np.nan, index=df.index)

    typical = (df['high'] + df['low'] + df['close']) / 3.0

    if 'real_volume' in df.columns and 'tick_volume' in df.columns:
        real = df['real_volume'].astype(float).fillna(0.0)
        tick = df['tick_volume'].astype(float).fillna(0.0)
        vol = real.where(real > 0, tick)
    elif 'real_volume' in df.columns:
        vol = df['real_volume'].astype(float).fillna(0.0)
    elif 'tick_volume' in df.columns:
        vol = df['tick_volume'].astype(float).fillna(0.0)
    else:
        return pd.Series(np.nan, index=df.index)

    if len(df) >= 1 and 'time' in df.columns and pd.api.types.is_datetime64_any_dtype(df['time']):
        try:
            day_key = df['time'].dt.date
            pv = (typical * vol).groupby(day_key).cumsum()
            vv = vol.groupby(day_key).cumsum()
            vwap = pv / vv.replace(0, np.nan)
            return vwap
        except Exception:
            pass

    # Fallback: janela deslizante simples quando nao ha 'time' diario confiavel
    pv = (typical * vol).rolling(window=max(1, period), min_periods=1).sum()
    vv = vol.rolling(window=max(1, period), min_periods=1).sum()
    return pv / vv.replace(0, np.nan)


def check_mm50_filter(df: pd.DataFrame, side_name: str) -> bool:
    """
    Filtro MM50: compras so com preco acima da MM50; vendas so abaixo.
    Espelho do filtro SMA200 ja aplicado em setups.py.
    Fallback permissivo (True) quando a media ainda nao formou ou esta desligado.
    """
    if not getattr(config, "MM50_ENABLED", True):
        return True

    if df is None or len(df) < 50 or 'sma50' not in df.columns:
        return True

    try:
        close = float(df['close'].iloc[-1])
        sma50 = float(df['sma50'].iloc[-1])
        if np.isnan(sma50):
            return True
        if side_name == "BUY":
            return bool(close > sma50)
        else:
            return bool(close < sma50)
    except Exception as e:
        logger.error(f"Erro ao checar filtro MM50: {e}")
        return True


def check_ifr9_filter(df: pd.DataFrame, side_name: str) -> bool:
    """
    Filtro IFR(9) de exaustao: em compras, IFR9 saindo da zona de sobrevenda
    (ex: subindo de <=30) confirma o setup; em vendas, saindo da sobrecompra
    (caindo de >=70) confirma.
    Fallback permissivo (True) quando o oscilador nao formou ou esta desligado.
    """
    if not getattr(config, "IFR9_ENABLED", True):
        return True

    if df is None or len(df) < 10 or 'rsi9' not in df.columns:
        return True

    try:
        rsi9 = df['rsi9'].astype(float)
        last = float(rsi9.iloc[-1])
        prev = float(rsi9.iloc[-2])
        if np.isnan(last) or np.isnan(prev):
            return True

        if side_name == "BUY":
            # Sair da sobrevenda: IFR subindo e partindo de zona <= 30
            return bool(last > prev and prev <= 30.0)
        else:
            return bool(last < prev and prev >= 70.0)
    except Exception as e:
        logger.error(f"Erro ao checar filtro IFR9: {e}")
        return True


def check_vwap_filter(df: pd.DataFrame, side_name: str) -> bool:
    """
    Filtro VWAP: preco esticado demais da VWAP veta a operacao (risco de
    reversao a media). Compra esticada (muito acima da VWAP) e vetada quando
    o afastamento supera {VWAP_MAX_DEVIATION_ATR} ATRs; venda espelha.
    Sem VWAP disponivel, retorna permissivo (True).
    """
    if not getattr(config, "VWAP_ENABLED", True):
        return True

    if df is None or len(df) == 0 or 'vwap' not in df.columns or 'atr' not in df.columns:
        return True

    try:
        close = float(df['close'].iloc[-1])
        vwap = float(df['vwap'].iloc[-1])
        atr = float(df['atr'].iloc[-1])
        if np.isnan(vwap) or np.isnan(atr) or atr <= 0:
            return True

        max_dev = getattr(config, "VWAP_MAX_DEVIATION_ATR", 2.0)
        deviation = abs(close - vwap) / atr
        return bool(deviation <= max_dev)
    except Exception as e:
        logger.error(f"Erro ao checar filtro VWAP: {e}")
        return True


def swing_levels(df: pd.DataFrame, lookback: int = 20) -> tuple:
    """
    Retorna (swing_high, swing_low) dos ultimos `lookback` candles fechados.
    Swing high = maior alta; swing low = menor minima no trecho.
    Retorna (nan, nan) se a janela nao tem dados suficientes.
    """
    if df is None or len(df) < 1:
        return (np.nan, np.nan)

    window = int(lookback)
    window = min(window, len(df))
    highs = df['high'].iloc[-window:].astype(float)
    lows = df['low'].iloc[-window:].astype(float)
    return (float(highs.max()), float(lows.min()))


def fib_extension_targets(entry: float, swing_high: float, swing_low: float,
                          is_long: bool) -> tuple:
    """
    Alvos por extensao de Fibonacci (spec 5.6):
    amplitude = swing_high - swing_low.
    LONG:  (entrada + amplitude, entrada + amplitude * 1.618)
    SHORT: (entrada - amplitude, entrada - amplitude * 1.618)

    Retorna (alvo1, alvo2). Com amplitude invalida (<=0 ou NaN), retorna
    (None, None) para que o chamador nao valide RRR sobre alvo inexistente.
    """
    try:
        amp = float(swing_high) - float(swing_low)
    except (TypeError, ValueError):
        return (None, None)
    if amp is None or np.isnan(amp) or amp <= 0:
        return (None, None)

    if is_long:
        return (float(entry) + amp, float(entry) + amp * 1.618)
    return (float(entry) - amp, float(entry) - amp * 1.618)
