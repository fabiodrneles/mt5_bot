"""Regra do dono, versao 4 (2026-10-24): "nao precisa ser 2x o risco, basta ter algum lucro".

So le historico. Uso: python check_exits.py SYM TF
Mesmo sinal (cruzamento da MME9, stop na maxima/minima do candle), saidas diferentes:
  alvo fixo de 0,25x a 1,5x o risco; primeiro fechamento no lucro; saida por tempo (1, 2, 4, 8 candles).
Mostra tambem quantos sinais CHEGARAM a ficar no lucro antes do stop (o "algum lucro" visto no grafico).
Cada sinal e avaliado sozinho, com custos reais. IS = 60% iniciais, OOS = 40% finais.
"""
import sys

import numpy as np

import check_ema9_filters as C
import research2 as R


def simulate_exits(sym, d, sig, dist):
    m = R._meta()[sym]
    o, h, l, c, t = d["o"], d["h"], d["l"], d["c"], d["t"]
    spr = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]])
    upu, comm = m["usd_per_unit"], m["comm_rt"]
    bar = np.median(np.diff(t))
    pause = np.r_[False, np.diff(t) > bar * 1.5]
    rules = [f"alvo {k}x" for k in (0.25, 0.5, 0.75, 1.0, 1.5)] + ["1o fechamento no lucro"] + \
            [f"sai apos {n} candles" for n in (1, 2, 4, 8)]
    out = {r: np.full(len(c), np.nan) for r in rules}
    touched = np.full(len(c), np.nan)
    for i in np.flatnonzero(sig):
        e = i + 1
        if e >= len(c) or (d.get("tf") != "D1" and d["hour"][e] == 0):
            continue
        dr = sig[i]
        entry = o[e] if not pause[e] else (max(o[e], c[i]) if dr > 0 else min(o[e], c[i]))
        risk = dist[i]
        sl = entry - dr * risk
        cost = spr[e]  # compra paga o spread na entrada; venda, na recompra (aproximado pelo mesmo valor)

        def usd(px):
            return (dr * (px - entry) - cost) * upu - comm

        pending = set(rules)
        best_fav = 0.0
        for j in range(e, min(len(c), e + 400)):
            hit_stop = (l[j] <= sl) if dr > 0 else (h[j] + spr[j] >= sl)
            fav = (h[j] - entry) if dr > 0 else (entry - l[j] - spr[j])
            if hit_stop:
                # pior caso: o stop vem antes do alvo dentro do mesmo candle
                px = (min(o[j], sl) if j > e else sl) if dr > 0 else (max(o[j], sl - spr[j]) if j > e else sl - spr[j])
                for r in list(pending):
                    out[r][i] = usd(px)
                pending.clear()
                break
            best_fav = max(best_fav, fav)
            for k in (0.25, 0.5, 0.75, 1.0, 1.5):
                r = f"alvo {k}x"
                if r in pending and fav >= k * risk:
                    out[r][i] = usd(entry + dr * k * risk)
                    pending.discard(r)
            close_pnl = usd(c[j])
            if "1o fechamento no lucro" in pending and close_pnl > 0:
                out["1o fechamento no lucro"][i] = close_pnl
                pending.discard("1o fechamento no lucro")
            for n in (1, 2, 4, 8):
                r = f"sai apos {n} candles"
                if r in pending and j - e + 1 >= n:
                    out[r][i] = close_pnl
                    pending.discard(r)
            if not pending:
                break
        touched[i] = float(best_fav * upu > cost * upu + comm + 0.01)  # chegou a ter >= 1 centavo liquido
    return out, touched


def st(p):
    p = p[np.isfinite(p)]
    if len(p) < 3 or p.std() == 0:
        return f"{len(p)} trades"
    w, lo = p[p > 0], p[p <= 0]
    t = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
    return (f"{len(p):5d} tr  acerto {np.mean(p > 0) * 100:5.1f}%  ganho medio ${w.mean() if len(w) else 0:.3f}  "
            f"perda media ${lo.mean() if len(lo) else 0:.3f}  total ${p.sum():+8.2f}  t {t:+5.2f}")


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    d = R.load(sym, tf)
    f = C.features(d)
    _, sig, dist = C.run_rule(sym, d, f, 0.0, "nenhum", "ambos")
    out, touched = simulate_exits(sym, d, sig, dist)
    has = np.isfinite(touched)
    idx = np.flatnonzero(has)
    cut = d["t"][idx[int(len(idx) * R.SPLIT)]]
    print(f"{sym} {tf}: {len(idx)} sinais. Chegaram a ficar >= 1 centavo no lucro antes do stop: "
          f"{np.nanmean(touched) * 100:.1f}%")
    for r, p in out.items():
        print(f"  {r:<24} IS {st(p[has & (d['t'] < cut)])}")
        print(f"  {'':<24} OOS {st(p[has & (d['t'] >= cut)])}")


if __name__ == "__main__":
    main()
