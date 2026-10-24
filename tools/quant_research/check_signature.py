"""Ideias do dono (2026-10-24) para o sinal da MME9, testadas como um robo poderia aplica-las:

A) "Assinatura" das grandes tendencias: cada sinal novo e comparado (k vizinhos mais proximos, k-NN) com
   os sinais ANTERIORES que ja terminaram; entra so se a fracao de vencedores entre os vizinhos for alta.
B) Lateralizacao por sequencia de stops: depois de L stops seguidos (ja terminados), para de operar ate o
   preco fechar fora da faixa daqueles sinais por mais de 0,5 ATR.
C) Regime pela eficiencia de Kaufman (ER) e pelo indice Choppiness: so opera se o mercado estiver em tendencia.

So le historico. Uso: python check_signature.py SYM TF
Cada sinal: stop na maxima/minima do candle, alvo 2x, custos reais. Parametros escolhidos nos 60% iniciais
dos sinais (IS) e medidos nos 40% finais (OOS).
"""
import itertools
import sys

import numpy as np

import check_ema9_filters as C
import research2 as R
import signal_mining as S

RR = 2.0


def outcomes_with_exit(sym, d, sig, dist):
    """Como signal_mining.outcomes, mas devolve tambem o indice do candle de saida (quando o resultado
    passa a ser conhecido)."""
    m = R._meta()[sym]
    o, h, l, c, t = d["o"], d["h"], d["l"], d["c"], d["t"]
    spr = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]])
    bar = np.median(np.diff(t))
    pause = np.r_[False, np.diff(t) > bar * 1.5]
    res, ex = np.full(len(c), np.nan), np.full(len(c), -1)
    for i in np.flatnonzero(sig):
        e = i + 1
        if e >= len(c) or (d.get("tf") != "D1" and d["hour"][e] == 0):
            continue
        dr = sig[i]
        entry = o[e] if not pause[e] else (max(o[e], c[i]) if dr > 0 else min(o[e], c[i]))
        sl, tp = entry - dr * dist[i], entry + dr * RR * dist[i]
        for j in range(e, len(c)):
            if dr > 0 and l[j] <= sl:
                px = min(o[j], sl) if j > e else sl
                break
            if dr > 0 and h[j] >= tp:
                px = tp
                break
            if dr < 0 and h[j] + spr[j] >= sl:
                px = max(o[j], sl - spr[j]) if j > e else sl - spr[j]
                break
            if dr < 0 and l[j] + spr[j] <= tp:
                px = tp - spr[j]
                break
        else:
            continue
        res[i] = (dr * (px - entry) - spr[e]) * m["usd_per_unit"] - m["comm_rt"]
        ex[i] = j
    return res, ex


def regime_features(d):
    c = d["c"]
    out = {}
    for n in (10, 20):
        change = np.abs(c - R.lag(c, n))
        vol = np.convolve(np.abs(np.diff(c, prepend=c[0])), np.ones(n), "full")[:len(c)]
        out[f"ER{n}"] = change / np.maximum(vol, 1e-12)            # 1 = tendencia limpa, 0 = lateral
    tr = R.true_range(d)
    s14 = np.convolve(tr, np.ones(14), "full")[:len(c)]
    rng14 = R.rmax(d["h"], 14) - R.rmin(d["l"], 14)
    out["CHOP"] = 100 * np.log10(np.maximum(s14, 1e-12) / np.maximum(rng14, 1e-12)) / np.log10(14)  # alto = lateral
    return out


def st(p):
    p = p[np.isfinite(p)]
    if len(p) < 3 or p.std() == 0:
        return f"{len(p):5d} trades"
    t = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
    return f"{len(p):5d} trades acerto {np.mean(p > 0) * 100:5.1f}% ${p.sum():+8.2f} t {t:+5.2f}"


def report(name, keep_by_param, res, is_m, oos_m):
    rows = []
    for par, keep in keep_by_param:
        pi, po = res[keep & is_m], res[keep & oos_m]
        pi_f = pi[np.isfinite(pi)]
        if len(pi_f) < 30 or pi_f.std() == 0:
            continue
        rows.append((pi_f.mean() / pi_f.std(ddof=1) * np.sqrt(len(pi_f)), par, pi, po))
    rows.sort(key=lambda r: -r[0])
    both = sum(1 for r in rows if np.nansum(r[2]) > 0 and np.nansum(r[3]) > 0)
    print(f"\n{name}: {len(rows)} variacoes; {both} lucram no IS e no OOS. Melhores no IS:")
    for _, par, pi, po in rows[:5]:
        print(f"   {par:<34} IS {st(pi)} | OOS {st(po)}")
    if rows:
        print(f"   -> escolhida pelo IS: {rows[0][1]} | OOS {st(rows[0][3])}")


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    d = R.load(sym, tf)
    f = C.features(d)
    _, sig, dist = C.run_rule(sym, d, f, 0.0, "nenhum", "ambos")
    res, ex = outcomes_with_exit(sym, d, sig, dist)
    has = np.isfinite(res)
    idx = np.flatnonzero(has)
    cut = d["t"][idx[int(len(idx) * R.SPLIT)]]
    is_m, oos_m = has & (d["t"] < cut), has & (d["t"] >= cut)
    print(f"{sym} {tf}: todos os sinais  IS {st(res[is_m])} | OOS {st(res[oos_m])}")

    feats = S.feature_table(d, f, sig)
    feats.update(regime_features(d))
    X = np.column_stack([feats[k] for k in feats])[idx]
    X = np.nan_to_num((X - np.nanmean(X[: int(len(idx) * R.SPLIT)], 0)) / (np.nanstd(X[: int(len(idx) * R.SPLIT)], 0) + 1e-12))
    win = (res[idx] > 0).astype(float)
    exit_bar = ex[idx]

    # A) k-NN online: memoria = sinais que ja terminaram antes do candle do sinal atual
    prob = {k: np.full(len(d["c"]), np.nan) for k in (15, 30, 60)}
    for n, i in enumerate(idx):
        done = np.flatnonzero(exit_bar[:n] < i)
        if len(done) < 60:
            continue
        dd = np.sum((X[done] - X[n]) ** 2, axis=1)
        order = np.argsort(dd)
        for k in prob:
            prob[k][i] = win[done[order[:k]]].mean()
    keep_a = [(f"k={k}, vizinhos vencedores >= {th:.0%}", np.nan_to_num(prob[k]) >= th)
              for k, th in itertools.product(prob, (0.35, 0.40, 0.45, 0.50))]
    report("A) Assinatura (k-NN dos sinais passados)", keep_a, res, is_m, oos_m)

    # B) pausa depois de L stops seguidos ate o preco sair da faixa
    keep_b = []
    for L in (2, 3, 4):
        keep = np.zeros(len(d["c"]), bool)
        A = R.atr(d, 14)
        for n, i in enumerate(idx):
            done = [m for m in range(n) if exit_bar[m] < i]
            last = done[-L:]
            if len(last) == L and all(win[m] == 0 for m in last):
                lo = d["l"][idx[last[0]]: i + 1].min()
                hi = d["h"][idx[last[0]]: i + 1].max()
                if lo - 0.5 * A[i] <= d["c"][i] <= hi + 0.5 * A[i]:
                    continue  # ainda dentro da regiao lateral
            keep[i] = True
        keep_b.append((f"pausa apos {L} stops", keep))
    report("B) Lateralizacao por sequencia de stops", keep_b, res, is_m, oos_m)

    # C) regime: eficiencia de Kaufman alta ou Choppiness baixo
    keep_c = [(f"ER{n} >= {th}", np.nan_to_num(feats[f"ER{n}"]) >= th) for n, th in itertools.product((10, 20), (0.3, 0.4, 0.5, 0.6))]
    keep_c += [(f"CHOP <= {th}", np.nan_to_num(feats["CHOP"], nan=100) <= th) for th in (38.2, 45, 50)]
    report("C) Regime de tendencia (Kaufman ER / Choppiness)", keep_c, res, is_m, oos_m)


if __name__ == "__main__":
    main()
