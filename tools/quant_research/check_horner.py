"""Metodo inspirado em Raghee Horner (Forex Trading for Maximum Profit, 2005): "onda" de MME34 (maxima,
fechamento e minima) e forca da tendencia pelo ANGULO da onda lido no relogio (12h-2h forte; perto de 3h fraca).
Opera A FAVOR da tendencia. Implementacao a partir da descricao publica do metodo; os detalhes podem diferir
do material original.

So le historico. Uso: python check_horner.py SYM TF
Entradas testadas (compra; venda espelhada):
  RECUO: onda inclinada para cima; a minima do candle toca a onda (<= MME34 da maxima) e o candle fecha acima
         da onda (> MME34 da maxima). Stop abaixo da MME34 da minima.
  MME9:  onda inclinada para cima e o candle fecha cruzando a MME9 para cima (regra do dono, a favor). Stop na
         minima do candle.
Inclinacao s = variacao da MME34 (fechamento) em N candles / (N x ATR); corte por quantil calibrado no IS
(os 50/30/20/10% mais inclinados). Alvos 1x e 2x o risco. IS = 60% iniciais, OOS = 40% finais.
"""
import itertools
import math
import sys

import numpy as np

import check_exits as X
import research2 as R


def clock(s):
    return 3 - math.degrees(math.atan(s)) / 30


def st(p):
    p = p[np.isfinite(p)]
    if len(p) < 3 or p.std() == 0:
        return f"{len(p):4d} tr"
    return f"{len(p):4d} tr acerto {np.mean(p > 0) * 100:5.1f}% ${p.sum():+7.2f} t {p.mean() / p.std(ddof=1) * np.sqrt(len(p)):+5.2f}"


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    d = R.load(sym, tf)
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    A = R.atr(d, 14)
    wh, wc, wl = R.ema(h, 34), R.ema(c, 34), R.ema(l, 34)
    e9 = R.ema(c, 9)
    nxt_o = np.r_[o[1:], np.nan]
    n = len(c)
    cut_i = int(n * R.SPLIT)
    cut = d["t"][cut_i]
    is_m, oos_m = d["t"] < cut, d["t"] >= cut
    rows = []
    for N, q, entry in itertools.product((5, 10, 20), (50, 70, 80, 90), ("RECUO", "MME9")):
        s = (wc - R.lag(wc, N)) / (N * A)
        thr = np.nanpercentile(np.abs(s[:cut_i]), q)
        up, dn = s >= thr, s <= -thr
        if entry == "RECUO":
            buy = up & (l <= wh) & (c > wh)
            sell = dn & (h >= wl) & (c < wl)
            stop_buy, stop_sell = nxt_o - wl, wh - nxt_o
        else:
            buy = up & (c > o) & (c > e9) & (R.lag((c < e9).astype(float)) == 1)
            sell = dn & (c < o) & (c < e9) & (R.lag((c > e9).astype(float)) == 1)
            stop_buy, stop_sell = nxt_o - l, h - nxt_o
        sig = np.zeros(n, int)
        sig[np.nan_to_num(buy).astype(bool)] = 1
        sig[np.nan_to_num(sell).astype(bool)] = -1
        dist = np.where(sig > 0, stop_buy, np.where(sig < 0, stop_sell, np.nan))
        sig[~(dist > 0)] = 0
        out, _ = X.simulate_exits(sym, d, sig, dist)
        rows.append(((entry, N, q, thr), out["alvo 1.0x"], out["alvo 1.5x"]))
    print(f"{sym} {tf}: {len(rows)} variacoes (entrada RECUO/MME9; N 5/10/20; os 50/30/20/10% mais inclinados)")
    for k, name in ((1, "alvo 1x"), (2, "alvo 1,5x")):
        scored = []
        for r in rows:
            p = r[k][is_m]
            p = p[np.isfinite(p)]
            if len(p) >= 30 and p.std() > 0:
                scored.append((p.mean() / p.std(ddof=1) * np.sqrt(len(p)), r))
        scored.sort(key=lambda x: -x[0])
        both = sum(1 for _, r in scored if np.nansum(r[k][is_m]) > 0 and np.nansum(r[k][oos_m]) > 0)
        print(f"\n{name}: {both} de {len(scored)} variacoes lucram no IS e no OOS. Melhores no IS:")
        for _, r in scored[:4]:
            entry, N, q, thr = r[0]
            print(f"   {entry:<5} N{N:<2} top {100 - q}% (inclinacao antes de {clock(thr):.1f}h)  "
                  f"IS {st(r[k][is_m])} | OOS {st(r[k][oos_m])}")


if __name__ == "__main__":
    main()
