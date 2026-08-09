import config


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
    return diff < config.FLAT_THRESHOLD_TICKS * tick_size


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