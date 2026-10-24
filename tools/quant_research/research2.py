"""Pesquisa ampla (rodada 3): 28 familias de estrategias x universo de margem baixa.

So le historico (data/*.npy, data/meta2.json); nenhuma ordem. Protocolo em PROTOCOLO2.md.
Uso:
    python research2.py run  [procs]        -> data/r2_<TF>.jsonl (todas as configuracoes)
    python research2.py one SYM TF FAM      -> imprime as configuracoes de uma familia
O simulador segue o de research.py (entrada na abertura seguinte, stop antes do alvo,
spread por candle, comissao, swap) com a rolagem tripla do swap corrigida.
"""
import itertools
import json
import os
import sys
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view as _sw

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
META = {}
SPLIT = 0.6
INTRADAY_TFS = ("M15", "M30", "H1", "H4")
SHORT_TFS = ("M15", "M30", "H1")  # timeframes com variantes intradiarias (fecham no fim do dia)
MIN_IS_TRADES = 20


def _meta():
    global META
    if not META:
        META = json.load(open(os.path.join(DATA, "meta2.json")))
    return META


# ---------------------------------------------------------------- dados
def _resample_h4(r, secs=4 * 3600):
    key = r["time"] // secs
    idx = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[idx[1:], len(r)]
    r2 = np.zeros(len(idx), dtype=r.dtype)
    r2["time"] = r["time"][idx]
    r2["open"] = r["open"][idx]
    r2["close"] = r["close"][ends - 1]
    r2["high"] = np.maximum.reduceat(r["high"], idx)
    r2["low"] = np.minimum.reduceat(r["low"], idx)
    r2["spread"] = np.maximum.reduceat(r["spread"], idx)
    r2["tick_volume"] = np.add.reduceat(r["tick_volume"], idx)
    return r2


def load(sym, tf):
    m = _meta()[sym]
    if tf == "H4":
        r = _resample_h4(np.load(os.path.join(DATA, f"{sym}_H1.npy")))
    elif tf == "M30":
        r = _resample_h4(np.load(os.path.join(DATA, f"{sym}_M15.npy")), 1800)
    else:
        r = np.load(os.path.join(DATA, f"{sym}_{tf}.npy"))
    spr = r["spread"].astype(float)
    if tf == "D1" or np.median(spr) == 0:
        h1r = np.load(os.path.join(DATA, f"{sym}_H1.npy"))
        h1 = h1r["spread"]
        pos = h1[h1 > 0]
        spr[:] = np.median(pos) if len(pos) else 0.0
        if tf == "D1":
            # O D1 abre no rollover, quando o spread dispara: entrada paga o spread tipico daquela hora.
            hr = (h1r["time"] % 86400) // 3600
            open_hr = int(np.median((r["time"] % 86400) // 3600))
            at_open = h1[(hr == open_hr) & (h1 > 0)]
            if len(at_open):
                spr[:] = max(spr[0], float(np.median(at_open)))
            # Reabertura depois do fim de semana/feriado: spread ainda maior (AUDJPY 62 pts x 3 normal).
            pause = np.r_[True, np.diff(h1r["time"]) > 3 * 3600]
            after = h1[pause & (h1 > 0)]
            gap_days = np.r_[False, np.diff(r["time"] // 86400) > 1]
            if len(after):
                spr[gap_days] = np.maximum(spr[gap_days], float(np.median(after)))
    else:
        pos = spr[spr > 0]
        spr[spr <= 0] = np.median(pos) if len(pos) else 0.0
    t = r["time"].astype(np.int64)
    day = t // 86400
    return dict(tf=tf, t=t, o=r["open"].astype(float), h=r["high"].astype(float), l=r["low"].astype(float),
                c=r["close"].astype(float), v=r["tick_volume"].astype(float), spr=spr * m["point"],
                day=day, dow=(day + 3) % 7, hour=(t % 86400) // 3600,
                month=(t.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64)))


# ---------------------------------------------------------------- indicadores
def sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.cumsum(np.r_[0.0, x])
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def ema(x, n):
    a = 2 / (n + 1)
    out = np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def wilder(x, n):
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + x[i]) / n
    return out


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    au = wilder(np.clip(d, 0, None), n)
    ad = wilder(np.clip(-d, 0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    r[ad == 0] = 100
    return r


def true_range(d):
    pc = np.r_[d["c"][0], d["c"][:-1]]
    return np.maximum(d["h"] - d["l"], np.maximum(abs(d["h"] - pc), abs(d["l"] - pc)))


def atr(d, n=14):
    return wilder(true_range(d), n)


def rmax(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = _sw(x, n).max(1)
    return out


def rmin(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = _sw(x, n).min(1)
    return out


def rstd(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = _sw(x, n).std(1)
    return out


def lag(x, k=1):
    return np.r_[np.full(k, np.nan), x[:-k]]


def lead(x, k=1):
    """Valor do candle seguinte: so para dados de calendario (dia, hora), conhecidos de antemao."""
    return np.r_[x[k:], np.full(k, np.nan)]


def adx(d, n=14):
    h, l = d["h"], d["l"]
    up = np.r_[0, h[1:] - h[:-1]]
    dn = np.r_[0, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = wilder(true_range(d), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * wilder(pdm, n) / tr
        ndi = 100 * wilder(ndm, n) / tr
        dx = 100 * abs(pdi - ndi) / (pdi + ndi)
    return wilder(np.nan_to_num(dx), n), pdi, ndi


def supertrend_dir(d, n=10, mult=3.0):
    a = atr(d, n)
    hl2 = (d["h"] + d["l"]) / 2
    c = d["c"]
    up = hl2 - mult * a
    dn = hl2 + mult * a
    direction = np.zeros(len(c), int)
    fu, fd = up.copy(), dn.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        if c[i] > fd[i - 1]:
            direction[i] = 1
        elif c[i] < fu[i - 1]:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1]
    return direction


def cross_flags(direction):
    prev = lag(direction.astype(float))
    return (direction == 1) & (prev != 1), (direction == -1) & (prev != -1)


# ---------------------------------------------------------------- simulador
def _rollovers(day_from, day_to, swap3):
    """Rolagens de swap entre dois dias (exclusivo no fim). Sab/Dom = 0; dia triplo = 3."""
    if day_to <= day_from:
        return 0
    days = np.arange(day_from, day_to)
    dow = (days + 3) % 7
    w = np.where(dow >= 5, 0, 1)
    w[dow == swap3] = 3
    return int(w.sum())


def simulate(sym, d, sig, stop, tgt, ex_long, ex_short, max_bars, intraday, cost=1.0):
    """sig[i] = +1/-1 no fechamento do candle i -> entra na abertura de i+1.

    Devolve array (n, 5): tempo de entrada, direcao, resultado US$, candles, risco US$ no stop.
    """
    m = _meta()[sym]
    o, h, l, c, day, t = d["o"], d["h"], d["l"], d["c"], d["day"], d["t"]
    # Conservador: o spread na abertura de um candle e o maior entre o do candle anterior e o dele
    # (os candles sao de bid e o campo spread do MT5 subestima o pico do rollover).
    # No D1 o spread de abertura ja vem modelado em load() (hora de abertura e reabertura do fim de semana).
    if d.get("tf") == "D1":
        spr = d["spr"] * cost
        spr_close = spr
    else:
        spr = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]]) * cost
        spr_close = np.maximum(d["spr"], np.r_[d["spr"][1:], d["spr"][-1:]]) * cost
    n = len(c)
    upu = m["usd_per_unit"]
    comm = m["comm_rt"] * cost
    swap3 = (int(m.get("swap3", 3)) + 6) % 7
    last_of_day = np.r_[day[1:] != day[:-1], True]
    bar = np.median(np.diff(t)) if n > 1 else 0
    # D1: todo candle abre depois de uma pausa e, em 37 de 72 CFDs, a abertura do historico e irreal
    # (gap medio -0,12 ATR desfeito pelo corpo). Entrada sempre pelo pior entre abertura e fechamento anterior.
    pause = np.r_[False, np.diff(t) > bar * 1.5] if d.get("tf") != "D1" else np.r_[False, np.ones(n - 1, bool)]
    rollover = (d["hour"] == 0) if d.get("tf") in INTRADAY_TFS and "hour" in d else np.zeros(n, bool)
    trades = []
    sig_idx = np.flatnonzero(sig)
    k = 0
    while k < len(sig_idx):
        i = sig_idx[k]
        if i + 1 >= n:
            break
        if intraday and last_of_day[i]:
            k += 1
            continue
        dr = sig[i]
        e = i + 1
        if rollover[e]:
            # Hora do rollover: o campo spread dos candles guarda o MINIMO da hora e esconde o pico
            # real (ticks EURGBP: 82-224 pts x ~30 no candle). Nao da para precificar: nao entra.
            k += 1
            continue
        sd = stop[i]
        if not np.isfinite(sd) or sd <= 0:
            k += 1
            continue
        entry = o[e]
        if pause[e]:
            # 1o candle depois de pausa: a abertura do historico e um print irreal (ex.: acoes na
            # abertura de NY com abertura ~1 abaixo do fechamento anterior). Entra pelo pior preco.
            entry = max(o[e], c[e - 1]) if dr > 0 else min(o[e], c[e - 1])
        sl = entry - dr * sd
        tp = entry + dr * tgt[i] if np.isfinite(tgt[i]) else np.nan
        exit_p = None
        j = e
        while j < n:
            if dr > 0:
                if l[j] <= sl:
                    exit_p = min(o[j], sl) if j > e else sl
                    break
                if np.isfinite(tp) and h[j] >= tp:
                    exit_p = max(o[j], tp) if j > e else tp
                    break
                if ex_long is not None and ex_long[j]:
                    exit_p = c[j]
                    break
            else:
                if h[j] + spr[j] >= sl:
                    exit_p = max(o[j], sl - spr[j]) if j > e else sl - spr[j]
                    break
                if np.isfinite(tp) and l[j] + spr[j] <= tp:
                    exit_p = tp - spr[j]
                    break
                if ex_short is not None and ex_short[j]:
                    exit_p = c[j] + spr_close[j] - spr[e]  # compra de volta no ask do fechamento
                    break
            if j - e + 1 >= max_bars or (intraday and last_of_day[j]):
                exit_p = c[j] + (spr_close[j] - spr[e] if dr < 0 else 0.0)
                break
            j += 1
        if exit_p is None:
            break
        pnl_price = dr * (exit_p - entry) - spr[e]
        rolls = _rollovers(day[e], day[j], swap3)
        s = m["swapL"] if dr > 0 else m["swapS"]
        if m["swap_mode"] == 1:
            sw_usd = s * m["point"] * upu * rolls
        else:
            sw_usd = entry * s / 100 / 360 * upu * rolls
        usd = pnl_price * upu - comm + sw_usd
        risk = (sd + spr[e]) * upu + comm
        trades.append((t[e], dr, usd, j - e + 1, risk))
        k = np.searchsorted(sig_idx, j + 1)
    return np.array(trades, dtype=float).reshape(-1, 5)


def stats(tr):
    if len(tr) == 0:
        return dict(n=0, net=0.0, pf=0.0, wr=0.0, dd=0.0, t=0.0, exp=0.0, worst=0.0, risk=0.0)
    p = tr[:, 2]
    eq = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0, eq])[1:]
    gw, gl = p[p > 0].sum(), -p[p < 0].sum()
    sd = p.std(ddof=1) if len(p) > 1 else 0.0
    return dict(n=int(len(p)), net=round(float(p.sum()), 3), pf=round(gw / gl, 2) if gl > 0 else 99.0,
                wr=round(float((p > 0).mean() * 100), 1), dd=round(float((peak - eq).max()), 3),
                t=round(float(p.mean() / sd * np.sqrt(len(p))), 2) if sd > 0 else 0.0,
                exp=round(float(p.mean()), 4), worst=round(float(p.min()), 3),
                risk=round(float(np.median(tr[:, 4])), 3))


# ---------------------------------------------------------------- familias
def strategies(d, tf):
    """Gera (familia, params, sig, stop, alvo, saida_long, saida_short, max_candles, intradiario)."""
    c, h, l, o, v = d["c"], d["h"], d["l"], d["o"], d["v"]
    n = len(c)
    nan = np.full(n, np.nan)
    A = atr(d, 14)
    s5, s20, s50, s200 = sma(c, 5), sma(c, 20), sma(c, 50), sma(c, 200)
    up200, dn200 = c > s200, c < s200
    xl5, xs5 = c > s5, c < s5
    intra_opts = (False, True) if tf in SHORT_TFS else (False,)
    out = []

    def add(fam, par, sig, stop, tgt=nan, xl=None, xs=None, mb=10 ** 6, intra=False):
        out.append((fam, par, sig, stop, tgt, xl, xs, mb, intra))

    def mk(long_mask, short_mask=None):
        s = np.zeros(n, int)
        s[np.nan_to_num(long_mask, nan=0).astype(bool)] = 1
        if short_mask is not None:
            s[np.nan_to_num(short_mask, nan=0).astype(bool)] = -1
        return s

    # ---------- reversao a media
    r2 = rsi(c, 2)
    for L, k, lo in itertools.product((5, 10), (2.0, 3.0), (True, False)):
        add("RSI2", dict(L=L, k=k, lo=lo), mk((r2 < L) & up200, None if lo else (r2 > 100 - L) & dn200),
            k * A, xl=xl5, xs=xs5, mb=15)
    for N, L in itertools.product((3, 4), (10, 20)):
        rn = rsi(c, N)
        add("RSIn", dict(N=N, L=L), mk((rn < L) & up200, (rn > 100 - L) & dn200), 2.5 * A,
            xl=rn > 70, xs=rn < 30, mb=15)
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        ibs = np.where(rng > 0, (c - l) / rng, 0.5)
    for th, filt in itertools.product((0.1, 0.2), (True, False)):
        lm = (ibs < th) & (up200 if filt else True)
        sm = (ibs > 1 - th) & (dn200 if filt else True)
        add("IBS", dict(th=th, sma200=filt), mk(lm, sm), 2.5 * A, xl=c > lag(h), xs=c < lag(l), mb=10)
    dnc = np.zeros(n, int)
    upc = np.zeros(n, int)
    for i in range(1, n):
        dnc[i] = dnc[i - 1] + 1 if c[i] < c[i - 1] else 0
        upc[i] = upc[i - 1] + 1 if c[i] > c[i - 1] else 0
    for N in (3, 4, 5):
        add("CONSEC", dict(N=N), mk((dnc == N) & up200, (upc == N) & dn200), 2.5 * A, xl=xl5, xs=xs5, mb=10)
    for N in (7, 10):
        add("DOUBLE7", dict(N=N), mk((c <= rmin(c, N)) & up200, (c >= rmax(c, N)) & dn200), 3.0 * A,
            xl=c >= rmax(c, N), xs=c <= rmin(c, N), mb=20)
    sd20 = rstd(c, 20)
    for dev, filt in itertools.product((2.0, 2.5), (True, False)):
        lm = (c < s20 - dev * sd20) & (up200 if filt else True)
        sm = (c > s20 + dev * sd20) & (dn200 if filt else True)
        add("BBMR", dict(dev=dev, sma200=filt), mk(lm, sm), 2.0 * A, xl=c >= s20, xs=c <= s20, mb=30)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (c - s20) / sd20
    for zt, k in itertools.product((1.5, 2.0), (2.0, 3.0)):
        add("ZSCORE", dict(z=zt, k=k), mk(z < -zt, z > zt), k * A, xl=z > 0, xs=z < 0, mb=30)
    gap = (o - lag(c)) / lag(A)
    for g in (0.5, 1.0):
        # O gap so e conhecido na abertura; sinalizar no candle anterior seria look-ahead. Por isso:
        # candle que abriu com gap e fechou ainda na direcao do gap -> aposta no fechamento do gap.
        lm = (gap < -g) & (c < lag(c))
        sm = (gap > g) & (c > lag(c))
        add("GAPFADE", dict(g=g), mk(lm, sm), 1.5 * A, xl=c >= lag(c, 2), xs=c <= lag(c, 2), mb=5)

    # ---------- tendencia / momento
    for N, k in itertools.product((20, 55), (2.0, 3.0)):
        hh, ll = lag(rmax(h, N)), lag(rmin(l, N))
        M = N // 2
        add("DONCH", dict(N=N, k=k), mk(c > hh, c < ll), k * A,
            xl=c < lag(rmin(l, M)), xs=c > lag(rmax(h, M)))
    for f, s in ((10, 50), (20, 100), (50, 200)):
        ef, es = ema(c, f), ema(c, s)
        above = ef > es
        prev = lag(above.astype(float))
        add("MACROSS", dict(f=f, s=s), mk(above & (prev == 0), (~above) & (prev == 1)), 3.0 * A,
            xl=~above, xs=above)
    for L in (20, 60, 120):
        mom = np.sign(c - lag(c, L))
        pm = lag(mom)
        add("TSMOM", dict(L=L), mk((mom > 0) & (pm <= 0), (mom < 0) & (pm >= 0)), 3.0 * A,
            xl=mom < 0, xs=mom > 0)
    macd = ema(c, 12) - ema(c, 26)
    sigl = ema(macd, 9)
    hist = macd - sigl
    for R in (1.5, 2.5):
        lm = (hist > 0) & (lag(hist) <= 0) & up200
        sm = (hist < 0) & (lag(hist) >= 0) & dn200
        add("MACD", dict(R=R), mk(lm, sm), 1.5 * A, tgt=R * 1.5 * A, mb=100)
    e20 = ema(c, 20)
    for mlt in (1.5, 2.0):
        add("KELTNER", dict(m=mlt), mk(c > e20 + mlt * A, c < e20 - mlt * A), 2.0 * A, xl=c < e20, xs=c > e20)
    for mlt in (2.0, 3.0):
        stl, sts = cross_flags(supertrend_dir(d, 10, mlt))
        add("SUPERT", dict(m=mlt), mk(stl, sts), 3.0 * A, xl=sts, xs=stl)
    ax, pdi, ndi = adx(d, 14)
    r14 = rsi(c, 14)
    for th in (20, 25):
        lm = (ax > th) & (pdi > ndi) & (r14 < 40)
        sm = (ax > th) & (ndi > pdi) & (r14 > 60)
        add("ADXPB", dict(th=th), mk(lm, sm), 2.0 * A, tgt=4.0 * A, mb=50)
    e50 = ema(c, 50)
    for k, R in itertools.product((1.0, 1.5), (1.5, 2.0, 3.0)):
        lm = (e20 > e50) & (l <= e20) & (c > e20) & up200
        sm = (e20 < e50) & (h >= e20) & (c < e20) & dn200
        add("PULLB", dict(k=k, R=R), mk(lm, sm), k * A, tgt=R * k * A, mb=200)

    # Regra do dono (cap. 14): candle que fecha cruzando a MME9 -> entra a favor; risco = tamanho do
    # candle do sinal; alvo = R x risco. E o gatilho do setup 9.1 (Larry Williams).
    e9 = ema(c, 9)
    x_dn = (c < o) & (c < e9) & (lag((c > e9).astype(float)) == 1)
    x_up = (c > o) & (c > e9) & (lag((c < e9).astype(float)) == 1)
    for R in (1.0, 2.0, 3.0):
        add("EMA9X", dict(R=R), mk(x_up, x_dn), rng.copy(), tgt=R * rng, mb=10 ** 6)

    # ---------- padroes de candle
    nr7 = rng <= rmin(rng, 7)
    inside = (h < lag(h)) & (l > lag(l))
    for R in (1.5, 2.5):
        lm = lag(nr7.astype(float)) == 1
        add("NR7", dict(R=R), mk(lm & (c > lag(h)) & (c > s50), lm & (c < lag(l)) & (c < s50)), 1.0 * A,
            tgt=R * A, mb=20)
        lm = lag(inside.astype(float)) == 1
        add("INSIDE", dict(R=R), mk(lm & (c > lag(h)) & (c > s50), lm & (c < lag(l)) & (c < s50)), 1.0 * A,
            tgt=R * A, mb=20)
    body = abs(c - o)
    bull_eng = (c > o) & (lag(c) < lag(o)) & (c >= lag(o)) & (o <= lag(c))
    bear_eng = (c < o) & (lag(c) > lag(o)) & (c <= lag(o)) & (o >= lag(c))
    lowband, upband = s20 - 2 * sd20, s20 + 2 * sd20
    for R in (1.5, 2.5):
        add("ENGULF", dict(R=R), mk(bull_eng & (rmin(l, 3) <= lowband) & up200,
                                    bear_eng & (rmax(h, 3) >= upband) & dn200), 1.5 * A, tgt=R * 1.5 * A, mb=30)
    low_wick = np.minimum(o, c) - l
    up_wick = h - np.maximum(o, c)
    hammer = (low_wick > 2 * body) & (ibs > 0.6) & (l <= rmin(l, 20))
    star = (up_wick > 2 * body) & (ibs < 0.4) & (h >= rmax(h, 20))
    for R in (1.5, 2.5):
        add("PINBAR", dict(R=R), mk(hammer, star), 1.0 * A, tgt=R * A, mb=30)

    # ---------- volume e fluxo (volume de ticks)
    v20 = sma(v, 20)
    for vm in (2.0, 3.0):
        cap = (v > vm * v20) & (rng > 1.5 * A)
        add("VOLCAP", dict(vm=vm), mk(cap & (c < o) & up200, cap & (c > o) & dn200), 2.5 * A,
            xl=xl5, xs=xs5, mb=10)
        hh, ll = lag(rmax(h, 20)), lag(rmin(l, 20))
        add("VOLBRK", dict(vm=vm), mk((c > hh) & (v > vm * v20 / 1.5), (c < ll) & (v > vm * v20 / 1.5)),
            2.0 * A, tgt=4.0 * A, mb=50)
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
    obv_up = obv > ema(obv, 20)
    for L in (5, 10):
        add("OBVRSI", dict(L=L), mk((r2 < L) & obv_up & up200, (r2 > 100 - L) & ~obv_up & dn200), 2.5 * A,
            xl=xl5, xs=xs5, mb=15)

    # ---------- calendario e intradiario
    if tf == "D1":
        mon = d["month"]
        last_day = np.r_[mon[1:] != mon[:-1], False]
        for N in (3, 5):
            add("TOM", dict(N=N), mk(lead(last_day.astype(float)) == 1), 3.0 * A, mb=N)
        for wd, side in itertools.product(range(5), (1, -1)):
            nxt = lead(d["dow"].astype(float)) == wd
            add("DOW", dict(wd=wd, side=side), mk(nxt) * side, 2.0 * A, mb=1)
    if tf in SHORT_TFS:
        hr = d["hour"]
        for hh_, k, side in itertools.product(range(24) if tf == "H1" else (), (1, 4), (1, -1)):
            nxt = lead(hr.astype(float)) == hh_
            add("HOD", dict(h=hh_, k=k, side=side), mk(nxt) * side, 1.5 * A, mb=k, intra=True)
        # VWAP intradiario (volume de ticks), reinicia a cada dia
        dayk = d["day"]
        tp_ = (h + l + c) / 3
        newd = np.r_[True, dayk[1:] != dayk[:-1]]
        grp = np.cumsum(newd)
        cpv = np.cumsum(tp_ * v)
        cv = np.cumsum(v)
        start = np.flatnonzero(newd)
        base_pv = np.r_[0, cpv][start][grp - 1]
        base_v = np.r_[0, cv][start][grp - 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            vwap = (cpv - base_pv) / (cv - base_v)
        for dev in (1.0, 1.5):
            add("VWAP", dict(dev=dev), mk(c < vwap - dev * A, c > vwap + dev * A), 1.5 * A,
                xl=c >= vwap, xs=c <= vwap, intra=True)
        # Rompimento da faixa da primeira hora do dia
        first_h = np.where(newd, h, np.nan)
        first_l = np.where(newd, l, np.nan)
        orh = first_h[start][grp - 1]
        orl = first_l[start][grp - 1]
        pos_in_day = np.arange(n) - start[grp - 1]
        brk_l = (c > orh) & (lag(c) <= lag(orh)) & (pos_in_day >= 1) & (pos_in_day <= 4)
        brk_s = (c < orl) & (lag(c) >= lag(orl)) & (pos_in_day >= 1) & (pos_in_day <= 4)
        for R in (1.0, 2.0):
            add("ORB", dict(R=R), mk(brk_l, brk_s), 1.0 * A, tgt=R * A, intra=True)
    # versao intradiaria das familias de reversao rapida no H1
    if True in intra_opts:
        base = [x for x in out if x[0] in ("RSI2", "IBS", "BBMR", "ZSCORE")]
        for fam, par, sig, stop, tgt, xl, xs, mb, _ in base:
            out.append((fam + "_I", par, sig, stop, tgt, xl, xs, mb, True))
    return out


# ---------------------------------------------------------------- execucao
def run_symbol(args):
    sym, tf = args
    t0 = time.time()
    try:
        d = load(sym, tf)
    except (FileNotFoundError, KeyError, ValueError, OSError):  # arquivo ausente ou corrompido
        return sym, tf, []
    n = len(d["c"])
    if n < 400:
        return sym, tf, []
    cut_t = d["t"][int(n * SPLIT)]
    rows = []
    for fam, par, sig, stop, tgt, xl, xs, mb, intra in strategies(d, tf):
        tr = simulate(sym, d, sig, stop, tgt, xl, xs, mb, intra)
        if len(tr) == 0:
            continue
        ins, oos = tr[tr[:, 0] < cut_t], tr[tr[:, 0] >= cut_t]
        p = tr[:, 2]
        sr = float(p.mean() / p.std(ddof=1)) if len(p) > 2 and p.std() > 0 else 0.0
        rows.append(dict(fam=fam, par=par, IS=stats(ins), OOS=stats(oos), sr=round(sr, 4), n=int(len(p))))
    yrs = (d["t"][-1] - d["t"][0]) / 3.156e7
    return sym, tf, [dict(sym=sym, tf=tf, yrs=round(yrs, 1), yrs_oos=round((d["t"][-1] - cut_t) / 3.156e7, 2),
                          secs=round(time.time() - t0, 1), rows=rows)]


def run(procs=3, tfs=("D1", "H4", "H1", "M30", "M15")):
    from multiprocessing import Pool
    syms = sorted(_meta())
    for tf in tfs:
        path = os.path.join(DATA, f"r2_{tf}.jsonl")
        done = set()
        if os.path.exists(path):
            done = {json.loads(x)["sym"] for x in open(path)}
        base = {"H4": "H1", "M30": "M15"}.get(tf, tf)
        todo = [(s, tf) for s in syms if s not in done and os.path.exists(os.path.join(DATA, f"{s}_{base}.npy"))]
        print(f"{tf}: {len(todo)} simbolos", flush=True)
        with Pool(procs) as pool, open(path, "a") as f:
            for sym, tf_, res in pool.imap_unordered(run_symbol, todo):
                for r in res:
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    print(f"{tf_} {sym} {len(r['rows'])} cfg {r['secs']}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 3,
            *([tuple(sys.argv[3].split(","))] if len(sys.argv) > 3 else []))
    elif sys.argv[1] == "one":
        sym, tf, fam = sys.argv[2:5]
        d = load(sym, tf)
        cut_t = d["t"][int(len(d["c"]) * SPLIT)]
        for f_, par, sig, stop, tgt, xl, xs, mb, intra in strategies(d, tf):
            if f_ != fam:
                continue
            tr = simulate(sym, d, sig, stop, tgt, xl, xs, mb, intra)
            print(par, "IS", stats(tr[tr[:, 0] < cut_t]), "OOS", stats(tr[tr[:, 0] >= cut_t]))
