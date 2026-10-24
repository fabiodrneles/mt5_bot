"""Pesquisa de estrategias com custos reais (spread por candle, comissao, swap).

Selecao de parametros SO na parte in-sample (60% inicial); o numero que importa
e o out-of-sample (40% final), que o otimizador nunca viu.
"""
import json, sys, itertools
import numpy as np

META = json.load(open("data/meta.json"))


# ---------------- dados ----------------
def load(sym, tf):
    if tf == "H4":
        r = np.load(f"data/{sym}_H1.npy")
        key = r["time"] // (4 * 3600)
        idx = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
        ends = np.r_[idx[1:], len(r)]
        r2 = np.zeros(len(idx), dtype=r.dtype)
        r2["time"] = r["time"][idx]; r2["open"] = r["open"][idx]
        r2["close"] = r["close"][ends - 1]
        r2["high"] = np.maximum.reduceat(r["high"], idx)
        r2["low"] = np.minimum.reduceat(r["low"], idx)
        r2["spread"] = np.maximum.reduceat(r["spread"], idx)
        r = r2
    else:
        r = np.load(f"data/{sym}_{tf}.npy")
    m = META[sym]
    spr = r["spread"].astype(float)
    if tf == "D1" or np.median(spr) == 0:
        h1 = np.load(f"data/{sym}_H1.npy")["spread"]
        spr[:] = np.median(h1[h1 > 0])
    else:
        med = np.median(spr[spr > 0])
        spr[spr <= 0] = med
    day = r["time"] // 86400
    return dict(t=r["time"], o=r["open"].astype(float), h=r["high"].astype(float),
                l=r["low"].astype(float), c=r["close"].astype(float),
                spr=spr * m["point"], day=day,
                dow=((day + 3) % 7))  # 0=seg


# ---------------- indicadores ----------------
def sma(x, n):
    out = np.full(len(x), np.nan)
    cs = np.cumsum(np.r_[0.0, x])
    out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out

def ema(x, n):
    a = 2 / (n + 1); out = np.empty(len(x)); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = np.clip(d, 0, None); dn = np.clip(-d, 0, None)
    au = np.empty(len(c)); ad = np.empty(len(c)); au[0] = ad[0] = 0
    for i in range(1, len(c)):
        au[i] = (au[i - 1] * (n - 1) + up[i]) / n
        ad[i] = (ad[i - 1] * (n - 1) + dn[i]) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + au / ad)
    r[ad == 0] = 100
    r[:n] = np.nan
    return r

def atr(d, n=14):
    pc = np.r_[d["c"][0], d["c"][:-1]]
    tr = np.maximum(d["h"] - d["l"], np.maximum(abs(d["h"] - pc), abs(d["l"] - pc)))
    out = np.full(len(tr), np.nan); out[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out

def rolling_max(x, n):
    from numpy.lib.stride_tricks import sliding_window_view as sw
    out = np.full(len(x), np.nan); out[n - 1:] = sw(x, n).max(1); return out

def rolling_min(x, n):
    from numpy.lib.stride_tricks import sliding_window_view as sw
    out = np.full(len(x), np.nan); out[n - 1:] = sw(x, n).min(1); return out

def rolling_std(x, n):
    from numpy.lib.stride_tricks import sliding_window_view as sw
    out = np.full(len(x), np.nan); out[n - 1:] = sw(x, n).std(1); return out


# ---------------- simulador ----------------
def swap_usd(sym, direction, price, nights):
    m = META[sym]
    s = m["swapL"] if direction > 0 else m["swapS"]
    if m["swap_mode"] == 1:      # pontos por lote
        per = s * m["point"] * m["usd_per_unit"]
    else:                         # % anual sobre o preco
        per = price * s / 100 / 360 * m["usd_per_unit"]
    return per * nights

def simulate(sym, d, sig, stop, tgt, ex_long, ex_short, max_bars, intraday):
    """sig[i] = +1/-1 no fechamento do candle i -> entra na abertura de i+1."""
    o, h, l, c, spr, day, t = d["o"], d["h"], d["l"], d["c"], d["spr"], d["day"], d["t"]
    n = len(c); m = META[sym]; upu = m["usd_per_unit"]
    last_of_day = np.r_[day[1:] != day[:-1], True]
    trades = []
    i = 0
    sig_idx = np.flatnonzero(sig)
    k = 0
    while k < len(sig_idx):
        i = sig_idx[k]
        if i + 1 >= n:
            break
        if intraday and last_of_day[i]:
            k += 1; continue
        dr = sig[i]; e = i + 1
        sd = stop[i]
        if not np.isfinite(sd) or sd <= 0:
            k += 1; continue
        entry = o[e]
        sl = entry - dr * sd
        tp = entry + dr * tgt[i] if np.isfinite(tgt[i]) else np.nan
        exit_p = None; j = e
        while j < n:
            # stop / alvo intrabar (stop primeiro: conservador)
            if dr > 0:
                if l[j] <= sl: exit_p = min(o[j], sl) if j > e else sl; break
                if np.isfinite(tp) and h[j] >= tp: exit_p = max(o[j], tp) if j > e else tp; break
                if ex_long is not None and ex_long[j]: exit_p = c[j]; break
            else:
                if h[j] + spr[j] >= sl: exit_p = max(o[j], sl - spr[j]) if j > e else sl - spr[j]; break
                if np.isfinite(tp) and l[j] + spr[j] <= tp:
                    exit_p = tp - spr[j]; break
                if ex_short is not None and ex_short[j]: exit_p = c[j]; break
            if j - e + 1 >= max_bars or (intraday and last_of_day[j]):
                exit_p = c[j]; break
            j += 1
        if exit_p is None:
            break
        pnl_price = dr * (exit_p - entry) - spr[e]
        nights = int(day[j] - day[e])
        usd = pnl_price * upu - m["comm_rt"] + swap_usd(sym, dr, entry, nights)
        trades.append((t[e], dr, usd, j - e + 1))
        # proximo sinal apos a saida
        k = np.searchsorted(sig_idx, j + 1)
    return trades


def stats(tr, balance=16.0):
    if not tr:
        return dict(n=0, net=0, pf=0, wr=0, dd=0, worst=0, maxcl=0, exp=0)
    p = np.array([x[2] for x in tr])
    eq = np.cumsum(p); peak = np.maximum.accumulate(np.r_[0, eq])[1:]
    gw = p[p > 0].sum(); gl = -p[p < 0].sum()
    cl = mx = 0
    for v in p:
        cl = cl + 1 if v < 0 else 0; mx = max(mx, cl)
    return dict(n=len(p), net=round(p.sum(), 3), pf=round(gw / gl, 2) if gl > 0 else 99,
                wr=round((p > 0).mean() * 100, 1), dd=round((peak - eq).max(), 3),
                worst=round(p.min(), 3), maxcl=mx, exp=round(p.mean(), 4))


# ---------------- estrategias ----------------
def strategies(d):
    c = d["c"]; A = atr(d, 14); s200 = sma(c, 200); s5 = sma(c, 5)
    r2 = rsi(c, 2); r14 = rsi(c, 14)
    nan = np.full(len(c), np.nan)
    out = []

    # S1 RSI2 reversao a media (Connors) com filtro SMA200
    for L, k, lo, intra in itertools.product((5, 10, 20), (2.0, 3.0), (True, False), (False, True)):
        sig = np.zeros(len(c), int)
        sig[(r2 < L) & (c > s200)] = 1
        if not lo: sig[(r2 > 100 - L) & (c < s200)] = -1
        out.append(("RSI2", dict(L=L, k=k, longonly=lo, intra=intra), sig, k * A, nan, c > s5, c < s5, 15, intra))

    # S2 Bollinger reversao: fecha fora da banda -> alvo media
    for dev, k, filt, intra in itertools.product((2.0, 2.5), (1.5, 2.5), (True, False), (False, True)):
        mid = sma(c, 20); sd = rolling_std(c, 20)
        lo_b = mid - dev * sd; up_b = mid + dev * sd
        sig = np.zeros(len(c), int)
        bl = (c < lo_b) & (r14 < 35); bs = (c > up_b) & (r14 > 65)
        if filt: bl &= c > s200; bs &= c < s200
        sig[bl] = 1; sig[bs] = -1
        out.append(("BBMR", dict(dev=dev, k=k, sma200=filt, intra=intra), sig, k * A, nan, c >= mid, c <= mid, 30, intra))

    # S3 Donchian breakout (tendencia)
    for N, k, intra in itertools.product((20, 55), (2.0, 3.0), (False, True)):
        hh = rolling_max(d["h"], N); ll = rolling_min(d["l"], N)
        hh1 = np.r_[np.nan, hh[:-1]]; ll1 = np.r_[np.nan, ll[:-1]]
        sig = np.zeros(len(c), int); sig[c > hh1] = 1; sig[c < ll1] = -1
        M = N // 2
        xl = c < np.r_[np.nan, rolling_min(d["l"], M)[:-1]]
        xs = c > np.r_[np.nan, rolling_max(d["h"], M)[:-1]]
        out.append(("DONCH", dict(N=N, k=k, intra=intra), sig, k * A, nan, xl, xs, 10 ** 6, intra))

    # S4 Pullback na tendencia (EMA20 > EMA50), alvo R multiplo
    e20 = ema(c, 20); e50 = ema(c, 50)
    for k, R, intra in itertools.product((1.0, 1.5), (1.5, 2.0, 3.0), (False, True)):
        sig = np.zeros(len(c), int)
        sig[(e20 > e50) & (d["l"] <= e20) & (c > e20) & (c > s200)] = 1
        sig[(e20 < e50) & (d["h"] >= e20) & (c < e20) & (c < s200)] = -1
        out.append(("PULLB", dict(k=k, R=R, intra=intra), sig, k * A, R * k * A, None, None, 200, intra))
    return out


def run(syms, tfs, split=0.6):
    rows = []
    for sym in syms:
        for tf in tfs:
            try:
                d = load(sym, tf)
            except FileNotFoundError:
                continue
            n = len(d["c"]); cut_t = d["t"][int(n * split)]
            for name, par, sig, stop, tgt, xl, xs, mb, intra in strategies(d):
                if tf == "D1" and intra:
                    continue
                tr = simulate(sym, d, sig, stop, tgt, xl, xs, mb, intra)
                ins = [x for x in tr if x[0] < cut_t]; oos = [x for x in tr if x[0] >= cut_t]
                rows.append(dict(sym=sym, tf=tf, strat=name, par=par, IS=stats(ins), OOS=stats(oos),
                                 yrs_oos=round((d["t"][-1] - cut_t) / 3.15e7, 2)))
            print(f"{sym} {tf} ok", file=sys.stderr, flush=True)
    return rows


if __name__ == "__main__":
    syms = sys.argv[1].split(","); tfs = sys.argv[2].split(",")
    rows = run(syms, tfs)
    json.dump(rows, open(sys.argv[3], "w"))
