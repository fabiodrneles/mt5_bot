import numpy as np
import pandas as pd
import pytest

from brain.trailing import aplicar_trailing, calcular_sl_trailing


def _df(close, low, high, ema9=None, sma21=None):
    n = len(close)
    return pd.DataFrame({
        "close": close,
        "low": low,
        "high": high,
        "ema9": ema9 if ema9 is not None else pd.Series([np.nan] * n),
        "sma21": sma21 if sma21 is not None else pd.Series([np.nan] * n),
    })


# ---------------------------------------------------------------------------
# calcular_sl_trailing
# ---------------------------------------------------------------------------

def test_candle_buy_usa_minima_do_penultimo_candle():
    df = _df(close=[100, 101, 102], low=[99, 100, 101], high=[101, 102, 103])
    sl, liquidar = calcular_sl_trailing(df, "BUY", modo="candle")
    assert sl == 100.0  # low[-2]
    assert liquidar is False


def test_candle_sell_usa_maxima_do_penultimo_candle():
    df = _df(close=[103, 102, 101], low=[102, 101, 100], high=[104, 103, 102])
    sl, liquidar = calcular_sl_trailing(df, "SELL", modo="candle")
    assert sl == 103.0  # high[-2]
    assert liquidar is False


def test_candle_precisa_de_dois_candles():
    df = _df(close=[100], low=[99], high=[101])
    sl, _ = calcular_sl_trailing(df, "BUY", modo="candle")
    assert sl is None


def test_ema9_liquida_quando_buy_perde_a_media():
    # close (99) < ema9 (100.5) -> perdeu a referencia, liquida
    df = _df(close=[100, 101, 99], low=[99, 100, 98], high=[101, 102, 100],
             ema9=[100.0, 100.5, 100.5])
    sl, liquidar = calcular_sl_trailing(df, "BUY", modo="ema9")
    assert liquidar is True
    assert sl is None


def test_ema9_sell_liquida_quando_preco_sobe():
    # close (101) > ema9 (100.0) -> SELL perdeu a referencia
    df = _df(close=[102, 101, 101], low=[101, 100, 100], high=[103, 102, 102],
             ema9=[102.0, 100.5, 100.0])
    sl, liquidar = calcular_sl_trailing(df, "SELL", modo="ema9")
    assert liquidar is True


def test_ema9_cola_no_valor_da_media_quando_nao_perde():
    df = _df(close=[100, 103, 104], low=[99, 102, 103], high=[101, 104, 105],
             ema9=[100.0, 101.0, 102.0])
    sl, liquidar = calcular_sl_trailing(df, "BUY", modo="ema9")
    assert sl == 102.0
    assert liquidar is False


def test_mm21_cola_na_sma21():
    df = _df(close=[100, 103, 104], low=[99, 102, 103], high=[101, 104, 105],
             sma21=[99.0, 100.0, 101.0])
    sl, liquidar = calcular_sl_trailing(df, "BUY", modo="mm21")
    assert sl == 101.0
    assert liquidar is False


# ---------------------------------------------------------------------------
# aplicar_trailing
# ---------------------------------------------------------------------------

def test_aplicar_nao_piora_o_sl_atual():
    df = _df(close=[100, 101, 102], low=[99, 100, 101], high=[101, 102, 103])
    # SL atual 100.5 > 100.0 (novo) -> nao aceita regressao
    novo, liquidar = aplicar_trailing(df, "BUY", sl_atual=100.5, modo="candle")
    assert novo is None
    assert liquidar is False


def test_aplicar_melhora_o_sl_candle():
    df = _df(close=[100, 101, 102], low=[99, 100, 101], high=[101, 102, 103])
    novo, liquidar = aplicar_trailing(df, "BUY", sl_atual=99.0, modo="candle")
    assert novo == 100.0
    assert liquidar is False


def test_aplicar_disabled_nao_move():
    df = _df(close=[100, 101, 102], low=[99, 100, 101], high=[101, 102, 103])
    novo, liquidar = aplicar_trailing(df, "BUY", sl_atual=99.0, modo="candle",
                                      enabled=False)
    assert novo is None
    assert liquidar is False


def test_aplicar_sem_sl_atual_aceita_primeiro_trailing():
    df = _df(close=[100, 101, 102], low=[99, 100, 101], high=[101, 102, 103])
    novo, liquidar = aplicar_trailing(df, "BUY", sl_atual=0.0, modo="candle")
    assert novo == 100.0
    assert liquidar is False


def test_aplicar_propaga_liquidacao():
    df = _df(close=[100, 101, 99], low=[99, 100, 98], high=[101, 102, 100],
             ema9=[100.0, 100.5, 100.5])
    novo, liquidar = aplicar_trailing(df, "BUY", sl_atual=99.0, modo="ema9")
    assert novo is None
    assert liquidar is True