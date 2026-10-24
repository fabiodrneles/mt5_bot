"""Setups quantitativos validados fora da amostra (v2.10.0).

Regras identicas ao simulador de pesquisa (memoria/wiki/arquitetura/
pesquisa-estrategias-lucrativas.md). Funcoes puras sobre o DataFrame de
candles FECHADOS: o ultimo candle (df.iloc[-1]) e o candle de sinal; a entrada
e a mercado logo apos o fechamento dele.

- PULLB  (HK50 H4): recuo a EMA20 a favor da tendencia EMA20/EMA50 + SMA200.
  SL = 1 x ATR14, TP = 2 x ATR14. Sai so por SL/TP.
- RSI2MR (US500 D1): IFR2 extremo a favor da SMA200 (Connors).
  SL = 2 x ATR14. Sai quando o fechamento cruza a SMA5 ou apos 15 candles.
"""
from typing import Optional

import numpy as np
import pandas as pd


def _ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def _rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff().fillna(0.0)
    up = d.clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = (-d).clip(lower=0.0).ewm(alpha=1.0 / n, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0.0, np.nan))
    return rsi.fillna(100.0)


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df['close'].shift(1).fillna(df['close'])
    tr = pd.concat([df['high'] - df['low'], (df['high'] - pc).abs(), (df['low'] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()


def signal_pullb(df: pd.DataFrame, params: dict) -> Optional[dict]:
    if len(df) < 200:
        return None
    c = df['close']
    e20, e50 = _ema(c, 20), _ema(c, 50)
    s200 = c.rolling(200).mean()
    atr = _atr(df)
    last = len(df) - 1
    a = float(atr.iloc[last]); cl = float(c.iloc[last])
    if not np.isfinite(a) or a <= 0 or not np.isfinite(s200.iloc[last]):
        return None
    k = params.get("sl_atr", 1.0); r = params.get("tp_r", 2.0)
    if e20.iloc[last] > e50.iloc[last] and df['low'].iloc[last] <= e20.iloc[last] < cl and cl > s200.iloc[last]:
        return {"setup": "PULLB", "action": "buy", "sl_dist": k * a, "tp_dist": r * k * a}
    if e20.iloc[last] < e50.iloc[last] and df['high'].iloc[last] >= e20.iloc[last] > cl and cl < s200.iloc[last]:
        return {"setup": "PULLB", "action": "sell", "sl_dist": k * a, "tp_dist": r * k * a}
    return None


def signal_rsi2mr(df: pd.DataFrame, params: dict) -> Optional[dict]:
    if len(df) < 200:
        return None
    c = df['close']
    rsi2 = _rsi(c, 2)
    s200 = c.rolling(200).mean()
    atr = _atr(df)
    last = len(df) - 1
    a = float(atr.iloc[last]); cl = float(c.iloc[last])
    if not np.isfinite(a) or a <= 0 or not np.isfinite(s200.iloc[last]):
        return None
    lvl = params.get("rsi_level", 5.0); k = params.get("sl_atr", 2.0)
    if rsi2.iloc[last] < lvl and cl > s200.iloc[last]:
        return {"setup": "RSI2MR", "action": "buy", "sl_dist": k * a, "tp_dist": None}
    if not params.get("long_only", False) and rsi2.iloc[last] > 100 - lvl and cl < s200.iloc[last]:
        return {"setup": "RSI2MR", "action": "sell", "sl_dist": k * a, "tp_dist": None}
    return None


def exit_rsi2mr(df: pd.DataFrame, is_buy: bool, params: dict) -> bool:
    """Saida da regra: fechamento cruzou a SMA5 a favor."""
    c = df['close']
    s5 = c.rolling(5).mean().iloc[-1]
    if not np.isfinite(s5):
        return False
    return bool(c.iloc[-1] > s5) if is_buy else bool(c.iloc[-1] < s5)


def signal_hour_of_week(df: pd.DataFrame, params: dict) -> Optional[dict]:
    """HOUR (calendario): entra na abertura do candle H1 de um dia da semana e hora fixos e sai no
    fechamento dele (max_bars = 1). Unico sobrevivente da varredura de calendario do cap. 14
    (USDJPY, segunda as 01h do servidor, compra): roda em ESTUDO, nao e rota validada.

    O sinal e o candle fechado imediatamente ANTERIOR ao horario de entrada (horario do servidor, o
    mesmo da pesquisa). SL protetor = sl_atr x ATR14 (a pesquisa saia so por tempo).
    """
    if len(df) < 20:
        return None
    t = pd.Timestamp(df['time'].iloc[-1])
    nxt = t + pd.Timedelta(hours=1)
    if nxt.dayofweek != params.get("weekday", 0) or nxt.hour != params.get("hour", 1):
        return None
    a = float(_atr(df).iloc[-1])
    if not np.isfinite(a) or a <= 0:
        return None
    action = params.get("side", "buy")
    return {"setup": "HOUR", "action": action, "sl_dist": params.get("sl_atr", 3.0) * a, "tp_dist": None}


SIGNALS = {"PULLB": signal_pullb, "RSI2MR": signal_rsi2mr, "HOUR": signal_hour_of_week}
EXITS = {"RSI2MR": exit_rsi2mr}


def evaluate(setup: str, df: pd.DataFrame, params: dict) -> Optional[dict]:
    fn = SIGNALS.get(setup)
    return fn(df, params or {}) if fn else None


def should_exit(setup: str, df: pd.DataFrame, is_buy: bool, params: dict) -> bool:
    fn = EXITS.get(setup)
    return fn(df, is_buy, params or {}) if fn else False
