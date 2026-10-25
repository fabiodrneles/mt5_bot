"""Setups do livro do Palex (Estrategias Operacionais, 2014) testados como o livro manda, em forex e na B3.

So le historico. Uso: python palex_setups.py [forex|b3|tudo]  -> data/palex_<mercado>.json e resumo.

Cada setup gera ordens a partir do candle fechado: ordem STOP (rompimento de maxima/minima) ou entrada no
FECHAMENTO, com stop e saida do livro:
  - alvo de projecao quando o livro especifica (Inside Day, Shark, Realizacao Frustrada, Latinha);
  - saida pela regra propria quando existe (cruzamento de medias, MM200, IFR2 > MM5, IFR14 sobrecomprado);
  - senao, "conduzir pela MME9" (marca a minima do candle que virou a MME9 contra; perdendo, sai).
Setups do livro nao testados (discricionarios ou sem regra completa no texto): Triple Screen, Three Line Bar,
Hilo Tranquilo, taticas de guerrilha, triangulos, congestoes e divergencias. Ver docs/validacao-palex.md.
"""
import json
import os
import sys

import numpy as np

import check_9x_b3 as B
import research2 as R

HERE = os.path.dirname(os.path.abspath(__file__))
SPLIT = 0.6


# ------------------------------------------------------------------ dados
def weekly(d):
    """Candles semanais a partir do diario (semana comecando na segunda)."""
    wk = (d["day"] + 3) // 7
    idx = np.flatnonzero(np.r_[True, wk[1:] != wk[:-1]])
    ends = np.r_[idx[1:], len(wk)]
    out = dict(t=d["t"][idx], day=d["day"][idx], o=d["o"][idx], c=d["c"][ends - 1],
               h=np.maximum.reduceat(d["h"], idx), l=np.minimum.reduceat(d["l"], idx),
               spr=np.maximum.reduceat(d["spr"], idx))
    return out


def ind(d):
    c, h, l, o = d["c"], d["h"], d["l"], d["o"]
    e9 = R.ema(c, 9)
    return dict(e9=e9, up9=np.r_[False, e9[1:] > e9[:-1]], dn9=np.r_[False, e9[1:] < e9[:-1]],
                m5=R.sma(c, 5), m9=R.sma(c, 9), m21=R.sma(c, 21), m50=R.sma(c, 50), m200=R.sma(c, 200),
                rsi2=R.rsi(c, 2), rsi14=R.rsi(c, 14), rng=h - l, body=c - o, atr=R.atr(d, 14),
                hmax=np.maximum.accumulate(h))


# ------------------------------------------------------------------ sinais
def signals(d, x, tf):
    """Lista de (i, setup, lado, tipo, gatilho, stop, alvo, saida, validade). tipo: 'stop' ou 'close'."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    n = len(c)
    m21, m50, m200 = x["m21"], x["m50"], x["m200"]
    rng = x["rng"]
    out = []
    add = out.append
    for i in range(205, n - 1):
        up21 = m21[i] > m21[i - 1] > m21[i - 2]
        dn21 = m21[i] < m21[i - 1] < m21[i - 2]
        # Retorno a MM21 + Fura-teto (p. 24): MM21 subindo, >= 2 candles de recuo, FECHA acima do fura-teto
        ft = h[i - 1] + (h[i - 1] - l[i - 1]) * 0.14
        if up21 and c[i - 1] < c[i - 2] and c[i - 2] < c[i - 3] and c[i] > ft:
            add((i, "FuraTeto", 1, "close", c[i], min(l[i - 2:i + 1]), None, "mme9", 1))
        ftv = l[i - 1] - (h[i - 1] - l[i - 1]) * 0.14
        if dn21 and c[i - 1] > c[i - 2] and c[i - 2] > c[i - 3] and c[i] < ftv:
            add((i, "FuraTeto", -1, "close", c[i], max(h[i - 2:i + 1]), None, "mme9", 1))
        # Harami e Engolfo de alta (p. 25, melhor no semanal): MM21 e MM50 subindo, recuo; entra acima da maxima
        if tf == "W1" and m21[i] > m21[i - 1] and m50[i] > m50[i - 1]:
            big_bear = (c[i - 1] < o[i - 1]) and (o[i - 1] - c[i - 1]) > 0.6 * rng[i - 1]
            harami = big_bear and c[i] > o[i] and h[i] <= o[i - 1] and l[i] >= c[i - 1]
            engolfo = (c[i - 1] < o[i - 1]) and c[i] > o[i] and o[i] <= c[i - 1] and c[i] >= o[i - 1]
            if harami or engolfo:
                add((i, "Harami/Engolfo", 1, "stop", h[i], min(l[i], l[i - 1]), None, "mme9", 3))
        # Cruzamento de medias (p. 30): MM5 ou MM9 cruza a MM21; entra no fechamento; sai no cruzamento contrario
        for fast, name in ((x["m5"], "Cruz MM5xMM21"), (x["m9"], "Cruz MM9xMM21")):
            if fast[i] > m21[i] and fast[i - 1] <= m21[i - 1]:
                add((i, name, 1, "close", c[i], np.nan, None, ("cross", name), 1))
            if fast[i] < m21[i] and fast[i - 1] >= m21[i - 1]:
                add((i, name, -1, "close", c[i], np.nan, None, ("cross", name), 1))
        # MM200 (p. 36): fecha cruzando a MM200; sai no cruzamento contrario
        if c[i] > m200[i] and c[i - 1] <= m200[i - 1]:
            add((i, "MM200", 1, "close", c[i], np.nan, None, ("mm200",), 1))
        if c[i] < m200[i] and c[i - 1] >= m200[i - 1]:
            add((i, "MM200", -1, "close", c[i], np.nan, None, ("mm200",), 1))
        # IFR14 + candle de reversao (p. 45): IFR14 na zona de sobrevenda + candle de reversao; stop na minima;
        # sai quando o IFR14 chega a sobrecompra (e perde a minima do candle de reversao de la)
        if x["rsi14"][i] <= 30 and c[i] > o[i] and (c[i] - l[i]) >= 0.6 * rng[i]:
            add((i, "IFR14+reversao", 1, "stop", h[i], l[i], None, ("rsi14",), 3))
        if x["rsi14"][i] >= 70 and c[i] < o[i] and (h[i] - c[i]) >= 0.6 * rng[i]:
            add((i, "IFR14+reversao", -1, "stop", l[i], h[i], None, ("rsi14",), 3))
        # IFR2 sobrevendido (Connors, p. 53): IFR2 < 5 acima da MM200, compra no fechamento, vende quando fecha
        # acima da MM5; sem stop (o livro nao usa)
        if x["rsi2"][i] < 5 and c[i] > m200[i]:
            add((i, "IFR2 sobrevendido", 1, "close", c[i], np.nan, None, ("rsi2",), 1))
        # Rompimento de topo historico (p. 70): compra 1 tick acima da maior maxima ja feita; stop largo
        th = x["hmax"][i - 1]
        if h[i] < th and i > 260:
            if h[i] >= th * 0.98 and c[i] > m200[i]:
                add((i, "Topo historico", 1, "stop", th, min(l[max(0, i - 20):i + 1]), None, "mme9", 5))
        # Iguana (Jeff Cooper, p. 74): minima dos ultimos 4 candles com abertura e fechamento acima de 75% do candle
        if rng[i] > 0 and l[i] <= min(l[i - 3:i + 1]) and min(o[i], c[i]) >= l[i] + 0.75 * rng[i]:
            add((i, "Iguana", 1, "stop", h[i], l[i], None, "mme9", 1))
        if rng[i] > 0 and h[i] >= max(h[i - 3:i + 1]) and max(o[i], c[i]) <= l[i] + 0.25 * rng[i]:
            add((i, "Iguana", -1, "stop", l[i], h[i], None, "mme9", 1))
        # Latinha chacoalhada (p. 79, semanal): menor amplitude dos ultimos 4 candles; rompe para um lado
        if tf == "W1" and rng[i] <= min(rng[i - 3:i]):
            add((i, "Latinha", 1, "stop", h[i], l[i], None, "mme9", 1))
            add((i, "Latinha", -1, "stop", l[i], h[i], None, "mme9", 1))
        # Inside Day (p. 90): barra contida na anterior; a favor da tendencia; alvo = projecao da barra mae
        if h[i] < h[i - 1] and l[i] > l[i - 1]:
            if up21:
                add((i, "Inside Day", 1, "stop", h[i], l[i], rng[i - 1], "alvo", 2))
            if dn21:
                add((i, "Inside Day", -1, "stop", l[i], h[i], rng[i - 1], "alvo", 2))
        # Shark (Walter Downs, p. 91): >= 3 candles cada um contido no anterior; rompe a maxima do 1o; alvo = amplitude
        if h[i] < h[i - 1] < h[i - 2] and l[i] > l[i - 1] > l[i - 2]:
            add((i, "Shark", 1, "stop", h[i - 2], l[i - 2], rng[i - 2], "alvo", 3))
            add((i, "Shark", -1, "stop", l[i - 2], h[i - 2], rng[i - 2], "alvo", 3))
        # Peg Leg (John Crane, p. 93): contra-tendencia; maxima de 20 candles e nova maxima em ate 3 candles;
        # venda abaixo da minima da nova maxima (valida 2 candles), stop acima da maxima
        prev20 = max(h[i - 23:i - 3]) if i >= 23 else np.inf
        if h[i] >= max(h[i - 20:i + 1]) and max(h[i - 3:i]) >= prev20:
            add((i, "Peg Leg", -1, "stop", l[i], h[i], None, "mme9", 2))
        low20 = min(l[i - 23:i - 3]) if i >= 23 else -np.inf
        if l[i] <= min(l[i - 20:i + 1]) and min(l[i - 3:i]) <= low20:
            add((i, "Peg Leg", 1, "stop", h[i], l[i], None, "mme9", 2))
        # Realizacao frustrada (p. 95): tendencia de alta (MM21 subindo); baixa-alta-baixa; rompe a maxima do
        # conjunto; stop na minima; alvo = amplitude do conjunto
        if up21 and c[i - 2] < o[i - 2] and c[i - 1] > o[i - 1] and c[i] < o[i]:
            hi, lo = max(h[i - 2:i + 1]), min(l[i - 2:i + 1])
            add((i, "Realizacao frustrada", 1, "stop", hi, lo, hi - lo, "alvo", 20))
        if dn21 and c[i - 2] > o[i - 2] and c[i - 1] < o[i - 1] and c[i] > o[i]:
            hi, lo = max(h[i - 2:i + 1]), min(l[i - 2:i + 1])
            add((i, "Realizacao frustrada", -1, "stop", lo, hi, hi - lo, "alvo", 20))
        # Key Buy (Velez/Capra, p. 97): tendencia de alta, nova maxima, depois 3+ barras com maximas e minimas
        # mais baixas; compra no rompimento da maxima da ultima barra
        if up21 and h[i] < h[i - 1] < h[i - 2] < h[i - 3] and l[i] < l[i - 1] < l[i - 2] < l[i - 3] \
                and h[i - 3] >= max(h[i - 23:i - 3]):
            add((i, "Key Buy", 1, "stop", h[i], l[i], None, "mme9", 2))
        if dn21 and l[i] > l[i - 1] > l[i - 2] > l[i - 3] and h[i] > h[i - 1] > h[i - 2] > h[i - 3] \
                and l[i - 3] <= min(l[i - 23:i - 3]):
            add((i, "Key Buy", -1, "stop", l[i], h[i], None, "mme9", 2))
    return out


# ------------------------------------------------------------------ execucao
def walk(d, x, sig, cost):
    """Uma ordem do sinal ate a saida. cost(entry, exit, side, e, j) -> (custo em preco). Devolve R e candles."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    i, setup, side, typ, trig, stop, tgt, exit_rule, valid = sig
    n = len(c)
    if typ == "close":
        e, entry = i, c[i]
    else:
        e, entry = None, None
        for j in range(i + 1, min(n, i + 1 + valid)):
            if (h[j] >= trig) if side > 0 else (l[j] <= trig):
                e, entry = j, (max(o[j], trig) if side > 0 else min(o[j], trig))
                break
        if e is None:
            return None
    has_stop = np.isfinite(stop)
    risk = (entry - stop) * side if has_stop else 2 * np.nan_to_num(x["atr"][e], nan=0)  # sem stop: R = 2 ATR
    # Risco minimo: candles sem amplitude (dados antigos do Yahoo, precos ajustados minusculos) dariam um risco
    # quase zero e um R absurdo. Exige risco >= 0,2% do preco e >= 0,1 ATR.
    atr_e = x["atr"][e]
    if not np.isfinite(risk) or risk <= max(0.002 * entry, 0.1 * (atr_e if np.isfinite(atr_e) else 0.0)):
        return None
    target = entry + side * tgt if tgt else None
    exit_level, px = None, None
    j = e + 1 if typ == "close" else e
    while j < n:
        first = j == e
        if has_stop and ((l[j] <= stop) if side > 0 else (h[j] >= stop)):
            px = stop if first else (min(o[j], stop) if side > 0 else max(o[j], stop))
            break
        if exit_level is not None and not first and ((l[j] <= exit_level) if side > 0 else (h[j] >= exit_level)):
            px = min(o[j], exit_level) if side > 0 else max(o[j], exit_level)
            break
        if target is not None and ((h[j] >= target) if side > 0 else (l[j] <= target)):
            px = target if first else (max(o[j], target) if side > 0 else min(o[j], target))
            break
        rule = exit_rule[0] if isinstance(exit_rule, tuple) else exit_rule
        if rule == "mme9" and j > e:
            turned = (x["dn9"][j] and x["up9"][j - 1]) if side > 0 else (x["up9"][j] and x["dn9"][j - 1])
            if turned:
                exit_level = l[j] if side > 0 else h[j]
            elif (x["up9"][j] if side > 0 else x["dn9"][j]) and exit_level is not None:
                exit_level = None
        elif rule == "cross":
            fast = x["m5"] if "MM5" in exit_rule[1] else x["m9"]
            if (fast[j] < x["m21"][j]) if side > 0 else (fast[j] > x["m21"][j]):
                px = c[j]
                break
        elif rule == "mm200":
            if (c[j] < x["m200"][j]) if side > 0 else (c[j] > x["m200"][j]):
                px = c[j]
                break
        elif rule == "rsi2":
            if c[j] > x["m5"][j]:
                px = c[j]
                break
        elif rule == "rsi14":
            if (x["rsi14"][j] >= 70) if side > 0 else (x["rsi14"][j] <= 30):
                px = c[j]
                break
        j += 1
    if px is None:
        return None
    return (side * (px - entry) - cost(entry, px, side, e, j)) / risk, j - e + 1, e, j, entry, px


# ------------------------------------------------------------------ mercados
def forex_universe():
    meta = R._meta()
    return [s for s in sorted(meta) if meta[s].get("group", "").startswith(("FX", "EURUSD"))
            and os.path.exists(os.path.join(R.DATA, f"{s}_D1.npy"))]


def forex_cost(sym, d):
    m = R._meta()[sym]
    swap3 = (int(m.get("swap3", 3)) + 6) % 7

    def cost(entry, px, side, e, j):
        rolls = R._rollovers(d["day"][e], d["day"][min(j, len(d["day"]) - 1)], swap3)
        s = m["swapL"] if side > 0 else m["swapS"]
        sw_px = (s * m["point"] if m["swap_mode"] == 1 else entry * s / 100 / 360) * rolls
        return d["spr"][e] + m["comm_rt"] / m["usd_per_unit"] - sw_px
    return cost


def b3_cost(entry, px, side, e, j):
    return B.COST_PER_SIDE * (entry + px)


def run_market(market):
    items = []
    if market == "forex":
        for sym in forex_universe():
            d = R.load(sym, "D1")
            items.append((sym, d, forex_cost(sym, d)))
    else:
        for tk in B.TICKERS:
            raw = B.fetch(tk)
            if raw:
                d = B.to_arrays(raw)
                if len(d["c"]) >= 500:
                    items.append((tk, d, b3_cost))
    trades = []
    for sym, d, cost in items:
        for tf, dd in (("D1", d), ("W1", weekly(d))):
            if len(dd["c"]) < 260:
                continue
            if tf == "W1" and market == "forex":
                cost_w = forex_cost(sym, dd)
            else:
                cost_w = cost
            x = ind(dd)
            cut = dd["t"][int(len(dd["t"]) * SPLIT)]
            for sig in signals(dd, x, tf):
                r = walk(dd, x, sig, cost_w if tf == "W1" else cost)
                if r is not None and np.isfinite(r[0]):
                    trades.append(dict(sym=sym, tf=tf, setup=sig[1], side=sig[2], oos=bool(dd["t"][sig[0]] >= cut),
                                       month=int(dd["t"][sig[0]] // (30 * 86400)), R=round(float(r[0]), 4)))
    return trades


def summarize(trades, market):
    def st(rs, months):
        a = np.array(rs)
        if len(a) < 20:
            return None
        mm = {}
        for m_, r_ in zip(months, rs):
            mm.setdefault(m_, []).append(r_)
        b = np.array([np.mean(v) for v in mm.values()])
        tm = b.mean() / b.std(ddof=1) * np.sqrt(len(b)) if len(b) > 2 and b.std() > 0 else 0.0
        return dict(n=len(a), R=round(float(a.mean()), 3), wr=round(float((a > 0).mean() * 100), 1),
                    t_mes=round(float(tm), 2))
    rows = []
    setups = sorted({t["setup"] for t in trades})
    for setup in setups:
        for tf in ("D1", "W1"):
            for side_name, sides in (("compra", (1,)), ("venda", (-1,)), ("ambos", (1, -1))):
                sel = [t for t in trades if t["setup"] == setup and t["tf"] == tf and t["side"] in sides]
                if not sel:
                    continue
                is_ = st([t["R"] for t in sel if not t["oos"]], [t["month"] for t in sel if not t["oos"]])
                oos = st([t["R"] for t in sel if t["oos"]], [t["month"] for t in sel if t["oos"]])
                if is_ or oos:
                    rows.append(dict(market=market, setup=setup, tf=tf, side=side_name, IS=is_, OOS=oos))
    return rows


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    for market in (("forex", "b3") if which == "tudo" else (which,)):
        trades = run_market(market)
        rows = summarize(trades, market)
        json.dump(dict(trades=len(trades), rows=rows), open(os.path.join(HERE, "data", f"palex_{market}.json"), "w"), indent=1)
        print(f"\n===== {market.upper()}: {len(trades)} trades")
        print(f"   {'setup':<22}{'TF':<4}{'lado':<8}{'IS: trades  R/trade  t(mes)':<30}{'OOS: trades  R/trade  t(mes)'}")
        for r in rows:
            if r["side"] == "ambos" and market == "b3":
                continue
            f = lambda s: f"{s['n']:5d}  {s['R']:+.3f}  {s['t_mes']:+5.2f}" if s else "   -"  # noqa: E731
            print(f"   {r['setup']:<22}{r['tf']:<4}{r['side']:<8}{f(r['IS']):<30}{f(r['OOS'])}")


if __name__ == "__main__":
    main()
