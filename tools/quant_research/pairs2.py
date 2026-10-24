"""Familia PAIRS (arbitragem estatistica) no D1: z-score do spread log entre dois ativos.

So le historico. Uso: python pairs2.py -> data/r2_pairs.json
beta e os lotes sao estimados SO no IS (60%). Cada perna usa um multiplo inteiro do lote minimo
(ate 3) que mais aproxima a neutralidade em dolar, porque com $16 nao ha lote fracionado.
"""
import itertools
import json
import os

import numpy as np

import research2 as R

PAIRS = [("EURUSD", "GBPUSD"), ("AUDUSD", "NZDUSD"), ("USOIL+", "UKOIL+"), ("US500", "US100"),
         ("US500", "US30"), ("EURJPY", "GBPJPY"), ("AUDCAD", "NZDCAD"), ("EU50", "GER40"),
         ("FR40", "EU50"), ("AUDJPY", "NZDJPY"), ("EURCAD", "GBPCAD"), ("USDCAD", "USOIL+"),
         ("ETHUSD", "BTCUSD"), ("UK100", "EU50"), ("JP225", "US500")]


def align(a, b):
    common, ia, ib = np.intersect1d(a["day"], b["day"], return_indices=True)
    return {k: a[k][ia] for k in a}, {k: b[k][ib] for k in b}


def leg_usd(sym, d, dr, e, j, lots):
    m = R._meta()[sym]
    entry, exit_p = d["o"][e], d["c"][j]
    pnl = dr * (exit_p - entry) - d["spr"][e]
    rolls = R._rollovers(d["day"][e], d["day"][j], (int(m.get("swap3", 3)) + 6) % 7)
    s = m["swapL"] if dr > 0 else m["swapS"]
    sw = s * m["point"] * m["usd_per_unit"] * rolls if m["swap_mode"] == 1 else \
        entry * s / 100 / 360 * m["usd_per_unit"] * rolls
    return lots * (pnl * m["usd_per_unit"] - m["comm_rt"] + sw)


def run_pair(sa, sb, L, zin, cut):
    a, b = align(R.load(sa, "D1"), R.load(sb, "D1"))
    n = len(a["c"])
    if n < 500:
        return None
    k = int(n * cut)
    la, lb = np.log(a["c"]), np.log(b["c"])
    beta = np.polyfit(lb[:k], la[:k], 1)[0]
    s = la - beta * lb
    mu, sd = R.sma(s, L), R.rstd(s, L)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (s - mu) / sd
    ma, mb = R._meta()[sa], R._meta()[sb]
    na, nb = a["c"][k] * ma["usd_per_unit"], b["c"][k] * mb["usd_per_unit"] * abs(beta)
    best = min(itertools.product((1, 2, 3), (1, 2, 3)), key=lambda q: abs(q[0] * na - q[1] * nb))
    trades, i = [], L
    while i < n - 1:
        if not np.isfinite(z[i]) or abs(z[i]) < zin:
            i += 1
            continue
        dr = -1 if z[i] > 0 else 1  # spread alto: vende A, compra B
        e = i + 1
        j = e
        while j < n - 1 and j - e < 30:
            if (dr > 0 and z[j] >= 0) or (dr < 0 and z[j] <= 0) or abs(z[j]) > zin + 2:
                break
            j += 1
        usd = leg_usd(sa, a, dr, e, j, best[0]) + leg_usd(sb, b, -dr, e, j, best[1])
        trades.append((a["t"][e], dr, usd, j - e + 1, 0.0))
        i = j + 1
    tr = np.array(trades, dtype=float).reshape(-1, 5)
    cut_t = a["t"][k]
    return dict(pair=f"{sa}/{sb}", L=L, z=zin, lots=best, beta=round(float(beta), 3),
                IS=R.stats(tr[tr[:, 0] < cut_t]), OOS=R.stats(tr[tr[:, 0] >= cut_t]),
                margin=round(best[0] * ma["margin"] + best[1] * mb["margin"], 2))


def main():
    meta = R._meta()
    rows = []
    for sa, sb in PAIRS:
        if sa not in meta or sb not in meta:
            print("sem dados:", sa, sb)
            continue
        for L, zin in itertools.product((20, 60), (1.5, 2.0)):
            try:
                r = run_pair(sa, sb, L, zin, R.SPLIT)
            except FileNotFoundError:
                r = None
            if r:
                rows.append(r)
                print(r["pair"], L, zin, r["lots"], "IS", r["IS"]["net"], r["IS"]["n"],
                      "OOS", r["OOS"]["net"], r["OOS"]["n"], "t", r["OOS"]["t"], "margem", r["margin"])
    json.dump(rows, open(os.path.join(R.DATA, "r2_pairs.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
