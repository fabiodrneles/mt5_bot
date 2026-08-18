"""Trailing Stop dinamico (spec 5.7).

Modulo stateless e puro (sem MT5) para decidir o proximo Stop Loss de uma
posicao aberta, barra a barra, apos o breakeven.

Modos (config.TRAILING_MODE):
  - "candle": BUY segue a minima do penultimo candle; SELL a maxima.
  - "ema9"  : cola o SL na EMA9 (colunar refere-se a "colar abaixo/acima").
  - "mm21"  : cola o SL na SMA21.
  - "atr"   : trailing baseado na volatilidade (1.5x ATR).

Se o preco perder a media de referencia do modo, o restante deve ser
liquidado a mercado (retorno `liquidar=True`).
"""


import pandas as pd


def _referencia(df: pd.DataFrame, modo: str):
    """Retorna a serie de referencia (ema9/sma21) conforme o modo."""
    if modo == "mm21":
        return df["sma21"]
    return df["ema9"]


def calcular_sl_trailing(df: pd.DataFrame, side: str, modo: str = "candle"):
    """Calcula o novo SL sugerido para uma posicao aberta.

    Args:
        df: DataFrame com ao menos 'high', 'low', 'close', 'ema9', 'sma21'.
        side: "BUY" ou "SELL".
        modo: "candle" | "ema9" | "mm21".

    Returns:
        (novo_sl, liquidar). novo_sl pode ser None se nao ha dados suficientes.
        liquidar=True indica que o preco perdeu a media de referencia e o
        restante deve ser fechado a mercado (spec 5.7).
    """
    if df is None or len(df) < 2:
        return None, False

    side = str(side).upper()
    close = float(df["close"].iloc[-1])

    # Liquida o restante se o preco perdeu a media de referencia do modo.
    if modo in ("ema9", "mm21"):
        ref = _referencia(df, modo).iloc[-1]
        if pd.isna(ref):
            return None, False
        ref = float(ref)
        if side == "BUY" and close < ref:
            return None, True
        if side == "SELL" and close > ref:
            return None, True

    if modo == "ema9":
        return float(ref), False
    if modo == "mm21":
        return float(ref), False
        
    if modo == "atr":
        atr = float(df["atr"].iloc[-1])
        if pd.isna(atr):
            return None, False
        if side == "BUY":
            return close - (atr * 1.5), False
        return close + (atr * 1.5), False

    # Modo "candle": SL = extremo do penultimo candle.
    if side == "BUY":
        return float(df["low"].iloc[-2]), False
    return float(df["high"].iloc[-2]), False


def aplicar_trailing(df: pd.DataFrame, side: str, sl_atual: float,
                     modo: str = "candle", enabled: bool = True):
    """Retorna o SL que deve ser enviado ao MT5 e se deve liquidar a posicao.

    Args:
        df: DataFrame de velas com indicadores.
        side: "BUY" ou "SELL".
        sl_atual: SL atual no MT5 (0.0 se sem SL).
        modo: "candle" | "ema9" | "mm21".
        enabled: se False, nao faz nada (trailing desligado).

    Returns:
        (proximo_sl, liquidar). proximo_sl pode ser None quando nada muda
        (sem dados, disabled, ou SL proposto nao melhora o atual).
    """
    if not enabled:
        return None, False

    novo_sl, liquidar = calcular_sl_trailing(df, side, modo)
    if liquidar:
        return None, True

    if novo_sl is None:
        return None, False

    # Nunca piorar o stop: so aceita se melhorar em relacao ao atual.
    if side == "BUY" and sl_atual and novo_sl <= sl_atual:
        return None, False
    if side == "SELL" and sl_atual and novo_sl >= sl_atual:
        return None, False

    return novo_sl, False