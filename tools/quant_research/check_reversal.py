"""Regra do dono, versao 3 (2026-10-24): o cruzamento da MME9 so vale como REVERSAO depois de uma
tendencia forte (setup 9.1 de Larry Williams). Mercado lateral fica de fora.

So le historico. Uso: python check_reversal.py SYM TF [AAAA-MM-DD]
"Tendencia forte anterior" vira criterio objetivo; a grade abaixo foi fixada ANTES de ver os resultados:
  N (candles olhados para tras)       10, 20, 40
  k (tamanho do movimento, em ATR)    2, 3, 4, 5
  persistencia (% de fechamentos do lado oposto da MME9 nesses N candles)   0 (ignora), 70%, 85%
  ADX >= 25 com DI a favor da tendencia anterior   nao / sim
Cada sinal e avaliado sozinho (stop na maxima/minima do candle, alvo 2x). A definicao e escolhida nos
60% iniciais (IS) e medida nos 40% finais (OOS).
"""
import datetime as dt
import itertools
import sys

import numpy as np

import check_ema9_filters as C
import research2 as R
import signal_mining as S

GRID = list(itertools.product((10, 20, 40), (2, 3, 4, 5), (0.0, 0.70, 0.85), (False, True)))


def prior_trend_masks(d, f, N, k, pers, use_adx):
    """Para COMPRA: queda >= k ATR nos N candles anteriores ao sinal (e o inverso para VENDA)."""
    c = d["c"]
    A = R.atr(d, 14)
    move = R.lag(c) - R.lag(c, N + 1)                       # variacao dos N candles ANTES do candle do sinal
    below = R.lag((c < f["e9"]).astype(float))
    frac_below = np.convolve(np.nan_to_num(below), np.ones(N), "full")[:len(c)] / N
    frac_above = 1 - frac_below
    down_before = (move <= -k * A) & (frac_below >= pers)
    up_before = (move >= k * A) & (frac_above >= pers)
    if use_adx:
        adx_prev, pdi_prev, ndi_prev = R.lag(f["adx"]), R.lag(f["pdi"]), R.lag(f["ndi"])
        down_before &= (adx_prev >= 25) & (ndi_prev > pdi_prev)
        up_before &= (adx_prev >= 25) & (pdi_prev > ndi_prev)
    return down_before, up_before


def stats(p):
    p = p[np.isfinite(p)]
    if len(p) < 3 or p.std() == 0:
        return dict(n=len(p), wr=0.0, net=float(np.nansum(p)), t=0.0)
    return dict(n=len(p), wr=float(np.mean(p > 0) * 100), net=float(p.sum()),
                t=float(p.mean() / p.std(ddof=1) * np.sqrt(len(p))))


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    day = sys.argv[3] if len(sys.argv) > 3 else None
    d = R.load(sym, tf)
    f = C.features(d)
    _, sig, dist = C.run_rule(sym, d, f, 0.0, "nenhum", "ambos")
    res = S.outcomes(sym, d, sig, dist)
    has = np.isfinite(res)
    idx = np.flatnonzero(has)
    cut = d["t"][idx[int(len(idx) * R.SPLIT)]]
    is_m, oos_m = has & (d["t"] < cut), has & (d["t"] >= cut)
    rows = []
    for N, k, pers, use_adx in GRID:
        dn, up = prior_trend_masks(d, f, N, k, pers, use_adx)
        keep = ((sig > 0) & dn) | ((sig < 0) & up)
        rows.append(((N, k, pers, use_adx), keep, stats(res[keep & is_m]), stats(res[keep & oos_m])))
    base_i, base_o = stats(res[is_m]), stats(res[oos_m])
    print(f"{sym} {tf}: sem filtro  IS {base_i['n']} trades acerto {base_i['wr']:.1f}% ${base_i['net']:+.2f} | "
          f"OOS {base_o['n']} acerto {base_o['wr']:.1f}% ${base_o['net']:+.2f}")
    print(f"{len(GRID)} definicoes de 'tendencia forte anterior'. As 10 melhores no IS (min. 30 trades):")
    print("   N   k   pers  ADX  | IS: trades acerto  lucro     t   | OOS: trades acerto  lucro     t")
    ok = [r for r in rows if r[2]["n"] >= 30]
    for (N, k, pers, use_adx), _, i, o in sorted(ok, key=lambda r: -r[2]["t"])[:10]:
        print(f"  {N:3d} {k:3d}  {pers:4.2f}  {'sim' if use_adx else 'nao'}  | {i['n']:5d} {i['wr']:5.1f}% {i['net']:+7.2f} {i['t']:+5.2f} | "
              f"{o['n']:5d} {o['wr']:5.1f}% {o['net']:+7.2f} {o['t']:+5.2f}")
    both = sum(1 for r in ok if r[2]["net"] > 0 and r[3]["net"] > 0)
    print(f"Definicoes com lucro no IS e no OOS: {both} de {len(ok)}")
    best = max(ok, key=lambda r: r[2]["t"])
    print(f"Escolhida pelo IS {best[0]} -> OOS {best[3]['n']} trades, acerto {best[3]['wr']:.1f}%, "
          f"lucro ${best[3]['net']:+.2f}, t {best[3]['t']:+.2f}")
    if day:
        d0 = int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp()) // 86400
        today = has & (d["day"] == d0)
        keep = best[1]
        print(f"\nDia {day} com a definicao escolhida {best[0]}:")
        for i in np.flatnonzero(today):
            hh = dt.datetime.fromtimestamp(int(d["t"][i]), dt.timezone.utc).strftime("%H:%M")
            print(f"   {hh} {'VENDA ' if sig[i] < 0 else 'COMPRA'} ${res[i]:+.2f}  {'ENTRA' if keep[i] else 'filtrado'}")


if __name__ == "__main__":
    main()
