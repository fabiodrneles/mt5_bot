import config
import logger




def close_prices(rates):
    return [r[4] for r in rates]


def high_prices(rates):
    return [r[2] for r in rates]


def low_prices(rates):
    return [r[3] for r in rates]


def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    result = values[:period]
    ema_value = sum(result) / period
    for v in values[period:]:
        ema_value = alpha * v + (1.0 - alpha) * ema_value
        result.append(ema_value)
    return result


def get_ema9(rates):
    closes = close_prices(rates)
    return ema(closes, config.EMA_PERIOD)


def get_ema21(rates):
    closes = close_prices(rates)
    return ema(closes, config.EMA_FILTER_PERIOD)


def get_ema9_slopes(ema9):
    if ema9 is None or len(ema9) < 4:
        return None, None
    slope_current = ema9[-1] - ema9[-2]
    slope_previous = ema9[-2] - ema9[-3]
    return slope_current, slope_previous


def check_virou_para_cima(ema9):
    slopes = get_ema9_slopes(ema9)
    if slopes is None:
        return False
    slope_current, slope_previous = slopes
    return slope_previous < 0 and slope_current > 0


def check_virou_para_baixo(ema9):
    slopes = get_ema9_slopes(ema9)
    if slopes is None:
        return False
    slope_current, slope_previous = slopes
    return slope_previous > 0 and slope_current < 0


def check_apontando_para_cima(ema9):
    slopes = get_ema9_slopes(ema9)
    if slopes is None:
        return False
    return slopes[0] > 0


def check_apontando_para_baixo(ema9):
    slopes = get_ema9_slopes(ema9)
    if slopes is None:
        return False
    return slopes[0] < 0


def check_virou_contra(ema9, is_long):
    if is_long:
        return check_virou_para_baixo(ema9)
    return check_virou_para_cima(ema9)


def check_flat(ema9, symbol_info):
    if ema9 is None or len(ema9) < 6:
        return False
    tick_size = symbol_info.trade_tick_size or symbol_info.point
    diff = abs(ema9[-1] - ema9[-5])
    multiplier = config.FLAT_THRESHOLD_MULTIPLIERS.get(config.TIMEFRAME_NAME, 1.0)
    threshold = config.FLAT_THRESHOLD_TICKS * multiplier
    return diff < threshold * tick_size


def check_filtro_ema21(close, ema21):
    if ema21 is None:
        return True
    return close > ema21[-1]


def check_filtro_ema21_venda(close, ema21):
    if ema21 is None:
        return True
    return close < ema21[-1]


def amplitude_candle(candle):
    return candle[2] - candle[3]


# --- Alvo Adaptativo ---

def adaptive_target_multiplier(rates, lookback=None):
    """Calcula um multiplicador de alvo adaptativo baseado na amplitude recente.

    Logica: compara a amplitude do candle de referencia com a mediana das
    ultimas N amplitudes. Se o candle de referencia for maior que a mediana,
    o alvo e reduzido proporcionalmente (mercado ja esticou). Se for menor,
    o alvo pode ser mantido ou levemente aumentado.

    Retorna (median_amplitude, multiplier) onde:
    - median_amplitude: amplitude mediana dos ultimos N candles
    - multiplier: fator para ajustar o PARTIAL_EXIT_TARGET (entre 0.6 e 1.2)
    """
    if lookback is None:
        lookback = config.ADAPTIVE_TARGET_LOOKBACK

    if len(rates) < lookback + 1:
        return None

    # Calcular amplitudes dos ultimos N candles (excluindo o mais recente que e o de referencia)
    amplitudes = []
    for i in range(len(rates) - lookback - 1, len(rates) - 1):
        if i >= 0:
            amp = rates[i][2] - rates[i][3]  # high - low
            if amp > 0:
                amplitudes.append(amp)

    if len(amplitudes) < 5:
        return None

    # Mediana (sem importar statistics para manter leve)
    amplitudes_sorted = sorted(amplitudes)
    mid = len(amplitudes_sorted) // 2
    if len(amplitudes_sorted) % 2 == 0:
        median_amp = (amplitudes_sorted[mid - 1] + amplitudes_sorted[mid]) / 2
    else:
        median_amp = amplitudes_sorted[mid]

    if median_amp <= 0:
        return None

    # Amplitude do ultimo candle FECHADO (rates[-2], pois rates[-1] esta formando)
    if len(rates) < 2:
        return None
    ref_amp = rates[-2][2] - rates[-2][3]
    if ref_amp <= 0:
        return None

    # Ratio: quanto o candle ref e comparado a mediana
    ratio = ref_amp / median_amp

    # Calcular multiplicador:
    # - Se ref_amp >> mediana (ratio > 1.5): mercado ja esticou, alvo menor (0.6x)
    # - Se ref_amp == mediana (ratio ~1.0): alvo normal (1.0x)
    # - Se ref_amp < mediana (ratio < 0.8): candle pequeno, alvo levemente maior (1.2x)
    if ratio > 1.5:
        multiplier = 0.6
    elif ratio > 1.2:
        multiplier = 0.8
    elif ratio < 0.6:
        multiplier = 1.2
    elif ratio < 0.8:
        multiplier = 1.1
    else:
        multiplier = 1.0

    return (median_amp, multiplier)


# --- ATR ---

def atr(rates, period=None):
    """Calcula ATR (Average True Range) sobre os rates.
    Retorna lista de valores ATR (um por candle apos o periodo inicial).
    """
    if period is None:
        period = config.ATR_PERIOD

    if len(rates) < period + 1:
        return None

    tr_values = []
    for i in range(1, len(rates)):
        high = rates[i][2]
        low = rates[i][3]
        prev_close = rates[i - 1][4]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    # Primeiro ATR e a media simples dos primeiros 'period' TRs
    atr_values = []
    atr_value = sum(tr_values[:period]) / period
    atr_values.append(atr_value)

    # ATRs subsequentes usam suavizacao exponencial
    for i in range(period, len(tr_values)):
        atr_value = (atr_value * (period - 1) + tr_values[i]) / period
        atr_values.append(atr_value)

    return atr_values


def get_atr_ratio(rates):
    """Calcula o ratio ATR_atual / ATR_media_50.
    Retorna (atr_current, atr_avg, ratio) ou None se dados insuficientes.
    """
    atr_values = atr(rates, config.ATR_PERIOD)
    if atr_values is None or len(atr_values) < config.ATR_AVG_PERIOD:
        return None

    atr_current = atr_values[-1]
    atr_avg = sum(atr_values[-config.ATR_AVG_PERIOD:]) / config.ATR_AVG_PERIOD

    if atr_avg == 0:
        return None

    ratio = atr_current / atr_avg
    return (atr_current, atr_avg, ratio)


# --- Pullback EMA9 (Setup 9.2) ---

def check_pullback_to_ema9(candle, ema9_value, is_long):
    """Verifica se o candle tocou/cruzou a EMA9 (pullback).
    Para compra: low <= ema9 (candle desceu ate a EMA9)
    Para venda: high >= ema9 (candle subiu ate a EMA9)
    """
    if is_long:
        return candle[3] <= ema9_value  # low <= ema9
    else:
        return candle[2] >= ema9_value  # high >= ema9


def check_ema9_retomou_direcao(ema9, is_long):
    """Verifica se a EMA9 retomou/manteve a direcao favoravel apos o pullback.
    Para compra: EMA9 apontando para cima
    Para venda: EMA9 apontando para baixo
    """
    if is_long:
        return check_apontando_para_cima(ema9)
    else:
        return check_apontando_para_baixo(ema9)


def count_ema9_against(ema9_history, is_long, max_look_back=5):
    """Conta quantos candles recentes a EMA9 esta apontando contra.
    Usado para decidir se cancela o WATCHING_92.
    """
    if ema9_history is None or len(ema9_history) < 3:
        return 0

    count = 0
    for i in range(min(max_look_back, len(ema9_history) - 1)):
        idx = -(i + 1)
        prev_idx = idx - 1
        if abs(prev_idx) > len(ema9_history):
            break
        slope = ema9_history[idx] - ema9_history[prev_idx]
        if is_long and slope < 0:
            count += 1
        elif not is_long and slope > 0:
            count += 1
        else:
            break  # Para de contar ao encontrar candle a favor
    return count


# --- RVOL (Volume Relativo) ---

def calculate_rvol(all_rates, lookback=None):
    """Calcula o RVOL (Volume Relativo) comparando o volume da vela atual com a media de N velas anteriores.
    Usa real_volume se disponivel (B3), senao tick_volume (Forex).
    Retorna (rvol_ratio, current_vol, avg_vol).
    """
    if lookback is None:
        lookback = getattr(config, "RVOL_LOOKBACK", 20)

    if len(all_rates) < lookback + 1:
        return (1.0, 0.0, 0.0)

    # Extrair volumes (indice 6 = real_volume, indice 5 = tick_volume)
    volumes = []
    for r in all_rates:
        real_vol = r[6] if len(r) > 6 else 0
        tick_vol = r[5] if len(r) > 5 else 0
        vol = float(real_vol) if real_vol > 0 else float(tick_vol)
        volumes.append(vol)

    current_vol = volumes[-1]
    past_volumes = volumes[-lookback - 1:-1]
    avg_vol = sum(past_volumes) / len(past_volumes) if past_volumes else 0.0

    if avg_vol == 0:
        return (1.0, current_vol, 0.0)

    rvol_ratio = current_vol / avg_vol
    return (rvol_ratio, current_vol, avg_vol)


# --- Setup 9.3 (Larry Williams) ---

def check_setup_93_buy(all_rates, ema9_values):
    """Verifica se ocorreu o gatilho do Setup 9.3 de Compra.
    EMA9 apontando para cima, seguida de recuo de velas sem virar EMA9 para baixo,
    e a vela atual rompe a maxima da vela anterior.
    """
    if not ema9_values or len(ema9_values) < 3 or len(all_rates) < 4:
        return False

    # EMA9 deve estar apontando para cima ou em retomada
    if not check_apontando_para_cima(ema9_values):
        return False

    max_pullback = getattr(config, "SETUP_93_MAX_PULLBACK_CANDLES", 2)
    # Verificar se as N velas anteriores tiveram fechamentos recuando
    # ex: candle[-2] close < candle[-3] close
    prev_close = all_rates[-2][4]
    ref_close = all_rates[-3][4]
    
    if prev_close < ref_close:
        # Vela atual (candle[-1]) deve romper a maxima da vela de recuo anterior (candle[-2][2])
        current_high = all_rates[-1][2]
        prev_high = all_rates[-2][2]
        if current_high > prev_high:
            return True

    return False


def check_setup_93_sell(all_rates, ema9_values):
    """Verifica se ocorreu o gatilho do Setup 9.3 de Venda.
    EMA9 apontando para baixo, seguida de recuo de velas sem virar EMA9 para cima,
    e a vela atual rompe a minima da vela anterior.
    """
    if not ema9_values or len(ema9_values) < 3 or len(all_rates) < 4:
        return False

    if not check_apontando_para_baixo(ema9_values):
        return False

    prev_close = all_rates[-2][4]
    ref_close = all_rates[-3][4]

    if prev_close > ref_close:
        current_low = all_rates[-1][3]
        prev_low = all_rates[-2][3]
        if current_low < prev_low:
            return True

    return False


# --- Filtro Multi-Timeframe (MTF) ---

def check_mtf_trend(symbol, current_tf_name, side_name):
    """Valida se a tendencia no timeframe superior (MTF) confirma a direcao da operacao."""
    if not getattr(config, "MTF_FILTER_ENABLED", True):
        return True

    try:
        import MetaTrader5 as mt5

        tf_map = getattr(config, "MTF_TIMEFRAME_MAP", {})
        mtf_tf_name = tf_map.get(current_tf_name, "H1")
        mtf_tf_const = config.AVAILABLE_TIMEFRAMES.get(mtf_tf_name, mt5.TIMEFRAME_H1)

        rates_count = getattr(config, "RATES_COUNT", 100)
        mtf_rates = mt5.copy_rates_from_pos(symbol, mtf_tf_const, 0, rates_count)

        if mtf_rates is None or len(mtf_rates) < 30:
            logger.warning(f"[{symbol}] Dados insuficientes para filtro MTF em {mtf_tf_name}.")
            return True  # Fallback permissivo

        ema9_mtf = get_ema9(mtf_rates)
        ema21_mtf = get_ema21(mtf_rates)

        if ema9_mtf is None or ema21_mtf is None:
            return True

        last_ema9 = ema9_mtf[-1]
        last_ema21 = ema21_mtf[-1]

        if side_name == "BUY":
            # Para compra, EMA9 no MTF deve estar acima da EMA21 e apontando para cima
            return (last_ema9 >= last_ema21) and check_apontando_para_cima(ema9_mtf)
        else:
            # Para venda, EMA9 no MTF deve estar abaixo da EMA21 e apontando para baixo
            return (last_ema9 <= last_ema21) and check_apontando_para_baixo(ema9_mtf)

    except Exception as e:
        logger.error(f"Erro ao checar filtro MTF para {symbol}: {e}")
        return True