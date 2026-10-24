"""Aplica os 7 criterios do PROTOCOLO2.md sobre data/r2_<TF>.jsonl.

Uso: python analyze2.py [saida.json]
Etapas: (1-3) selecao so no IS e checagem OOS/robustez sobre os resultados gravados;
(4-7) para quem passou, re-simula com custos 1,5x/2x, walk-forward ancorado de 5 dobras,
Deflated Sharpe Ratio e Monte Carlo da conta de $16.
"""
import json
import math
import os
import sys
from statistics import NormalDist

import numpy as np

import research2 as R

N01 = NormalDist()
GAMMA = 0.5772156649
BAL = 16.0


def load_rows(tf):
    path = os.path.join(R.DATA, f"r2_{tf}.jsonl")
    return [json.loads(x) for x in open(path)] if os.path.exists(path) else []


def tstat(p):
    return float(p.mean() / p.std(ddof=1) * math.sqrt(len(p))) if len(p) > 2 and p.std() > 0 else 0.0


def stage_a(rec):
    """Criterios 1-3 por (simbolo, timeframe, familia). Devolve candidatos."""
    fams = {}
    for row in rec["rows"]:
        fams.setdefault(row["fam"], []).append(row)
    out = []
    for fam, rows in fams.items():
        eligible = [r for r in rows if r["IS"]["n"] >= R.MIN_IS_TRADES]
        if not eligible:
            continue
        best = max(eligible, key=lambda r: r["IS"]["t"])
        robust = sum(1 for r in rows if r["IS"]["net"] > 0 and r["OOS"]["net"] > 0) / len(rows)
        o, i = best["OOS"], best["IS"]
        c1 = o["n"] >= 30 and o["net"] > 0 and o["pf"] >= 1.2 and o["t"] >= 2.0
        c2 = i["net"] > 0
        c3 = robust >= 0.5
        out.append(dict(sym=rec["sym"], tf=rec["tf"], fam=fam, par=best["par"], IS=i, OOS=o, robust=round(robust, 2),
                        sr=best["sr"], n=best["n"], yrs_oos=rec["yrs_oos"], c1=c1, c2=c2, c3=c3))
    return out


def family_configs(d, tf, fam):
    return [x for x in R.strategies(d, tf) if x[0] == fam]


def walk_forward(sym, d, tf, fam, folds=5):
    """Ancorado: dobra f usa [0, f+1)/(folds+1) para escolher e o pedaco seguinte para medir."""
    cfgs = family_configs(d, tf, fam)
    trs = [R.simulate(sym, d, *x[2:]) for x in cfgs]
    t = d["t"]
    edges = [t[min(len(t) - 1, int(len(t) * k / (folds + 1)))] for k in range(folds + 2)]
    edges[-1] = t[-1] + 1
    res = []
    for f in range(1, folds + 1):
        is_end, oos_end = edges[f], edges[f + 1]
        best, best_t = None, -1e9
        for tr in trs:
            p = tr[tr[:, 0] < is_end, 2]
            if len(p) >= 10:
                ts = tstat(p)
                if ts > best_t:
                    best, best_t = tr, ts
        if best is None:
            res.append(0.0)
            continue
        sel = best[(best[:, 0] >= is_end) & (best[:, 0] < oos_end), 2]
        res.append(round(float(sel.sum()), 3))
    return res


def dsr(p, sr_var, n_trials):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) do Sharpe por trade."""
    n = len(p)
    if n < 10 or p.std() == 0 or n_trials < 2:
        return 0.0
    sr = p.mean() / p.std(ddof=1)
    g3 = float(((p - p.mean()) ** 3).mean() / p.std() ** 3)
    g4 = float(((p - p.mean()) ** 4).mean() / p.std() ** 4)
    sr0 = math.sqrt(sr_var) * ((1 - GAMMA) * N01.inv_cdf(1 - 1 / n_trials)
                               + GAMMA * N01.inv_cdf(1 - 1 / (n_trials * math.e)))
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return float(N01.cdf((sr - sr0) * math.sqrt(n - 1) / den))


def monte_carlo(p, risk, margin, per_year, years=2, sims=5000, seed=7):
    """Ruina = patrimonio abaixo de margem + 1 stop. Lote minimo fixo."""
    rng = np.random.default_rng(seed)
    k = max(1, int(round(per_year * years)))
    draws = rng.choice(p, size=(sims, k), replace=True)
    eq = BAL + np.cumsum(draws, axis=1)
    ruined = (eq < margin + risk).any(axis=1)
    return float(ruined.mean()), float(np.median(eq[:, -1])), float(np.percentile(eq[:, -1], 5))


def main(out_path):
    meta = R._meta()
    report = dict(tested={}, candidates=[], promising=[], cells={})
    for tf in ("D1", "H4", "H1"):
        recs = load_rows(tf)
        if not recs:
            continue
        all_sr = [r["sr"] for rec in recs for r in rec["rows"] if r["n"] >= 20]
        n_trials = sum(len(rec["rows"]) for rec in recs)
        sr_var = float(np.var(all_sr)) if all_sr else 0.0
        report["tested"][tf] = dict(symbols=len(recs), configs=n_trials, sr_std=round(math.sqrt(sr_var), 4))
        cells = [c for rec in recs for c in stage_a(rec)]
        report["cells"][tf] = dict(total=len(cells), c1=sum(c["c1"] for c in cells),
                                   c12=sum(c["c1"] and c["c2"] for c in cells),
                                   c123=sum(c["c1"] and c["c2"] and c["c3"] for c in cells))
        n_cells = len(cells)
        for c in [c for c in cells if c["c1"] and c["c2"] and c["c3"]]:
            sym = c["sym"]
            d = R.load(sym, tf)
            cfg = next(x for x in family_configs(d, tf, c["fam"]) if x[1] == c["par"])
            cut_t = d["t"][int(len(d["c"]) * R.SPLIT)]
            stress = {}
            for mult in (1.5, 2.0):
                tr = R.simulate(sym, d, *cfg[2:], cost=mult)
                stress[str(mult)] = round(float(tr[tr[:, 0] >= cut_t, 2].sum()), 3)
            c4 = stress["1.5"] > 0
            wf = walk_forward(sym, d, tf, c["fam"])
            c5 = sum(wf) > 0 and sum(1 for x in wf if x > 0) >= 3
            tr = R.simulate(sym, d, *cfg[2:])
            p = tr[:, 2]
            dsr_full = dsr(p, sr_var, n_trials)
            dsr_cells = dsr(p, sr_var, n_cells)  # informativo: N efetivo ~ celulas (simbolo x familia)
            c6 = dsr_full >= 0.95
            oos = tr[tr[:, 0] >= cut_t]
            risk = float(np.median(tr[:, 4]))
            per_year = len(oos) / max(c["yrs_oos"], 0.1)
            ruin, med_end, p5_end = monte_carlo(oos[:, 2], risk, meta[sym]["margin"], per_year)
            c7 = risk <= 1.6 and ruin < 0.05
            # generalizacao: mesma familia e parametro nos outros simbolos do mesmo grupo (so informativo)
            grp = meta[sym].get("group", "")
            same = [r for rec in recs if rec["sym"] != sym and meta.get(rec["sym"], {}).get("group") == grp
                    for r in rec["rows"] if r["fam"] == c["fam"] and r["par"] == c["par"] and r["OOS"]["n"] >= 10]
            gen = f"{sum(1 for r in same if r['OOS']['net'] > 0)}/{len(same)}"
            c.update(stress=stress, c4=c4, wf=wf, c5=c5, dsr=round(dsr_full, 3), dsr_cells=round(dsr_cells, 3),
                     c6=c6, risk=round(risk, 3), ruin=round(ruin, 3), end_med=round(med_end, 2),
                     end_p5=round(p5_end, 2), c7=c7, gen=gen, group=grp, margin=meta[sym]["margin"])
            ok = c4 and c5 and c6 and c7
            (report["candidates"] if ok else report["promising"]).append(c)
            print(tf, sym, c["fam"], c["par"], "OOS", c["OOS"]["net"], "t", c["OOS"]["t"], "wf", wf,
                  "dsr", c["dsr"], "risk", c["risk"], "ruin", c["ruin"], "->", "APROVADA" if ok else "promissora",
                  flush=True)
    json.dump(report, open(out_path, "w"), indent=1, default=float)
    print(json.dumps(dict(tested=report["tested"], cells=report["cells"], candidates=len(report["candidates"]),
                          promising=len(report["promising"])), indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(R.DATA, "a2.json"))
