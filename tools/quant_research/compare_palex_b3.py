"""Setups do Palex na B3 em CARTEIRA contra CDI e Ibovespa (2026-10-24). So le dados publicos.

Uso: python compare_palex_b3.py -> data/compare_palex_b3.json e tabela.
Mesma construcao do compare_b3.py: peso igual entre as acoes listadas em cada dia, uma posicao por vez por acao
(regras do palex_setups.py), dinheiro fora da posicao no CDI, custo 0,05% por lado, sem imposto de renda.
So setups de COMPRA no diario.
"""
import datetime as dt
import json
import os

import numpy as np

import check_9x_b3 as B
import compare_b3 as C
import palex_setups as P

SETUPS = ["Cruz MM5xMM21", "Cruz MM9xMM21", "MM200", "IFR2 sobrevendido", "FuraTeto", "IFR14+reversao",
          "Topo historico", "Peg Leg", "Iguana", "Key Buy", "Realizacao frustrada"]


def daily_returns(d, setup):
    x = P.ind(d)
    n = len(d["c"])
    ret = np.full(n, np.nan)
    busy = -1
    for sig in P.signals(d, x, "D1"):
        if sig[1] != setup or sig[2] != 1 or sig[0] <= busy:
            continue
        r = P.walk(d, x, sig, P.b3_cost)
        if r is None or not np.isfinite(r[0]):
            continue
        _, _, e, j, entry, px = r
        j = min(j, n - 1)
        for k in range(e, j + 1):
            prev = entry if k == e else d["c"][k - 1]
            cur = px if k == j else d["c"][k]
            rr = cur / prev - 1 if k > e or sig[3] == "stop" else 0.0
            if k == e:
                rr -= B.COST_PER_SIDE
            if k == j:
                rr -= B.COST_PER_SIDE
            ret[k] = rr
        busy = j
    return ret


def main():
    cdi, ib = C.cdi_daily(), C.ibov()
    stocks = {}
    for tk in B.TICKERS:
        raw = B.fetch(tk)
        if raw:
            d = B.to_arrays(raw)
            if len(d["c"]) >= 500:
                stocks[tk] = d
    cal = sorted(set().union(*[set(d["day"].tolist()) for d in stocks.values()]) & set(cdi) & set(ib))
    idx = {day: k for k, day in enumerate(cal)}
    T = len(cal)
    cdi_r = np.array([cdi[day] for day in cal])
    ib_c = np.array([ib[day] for day in cal])
    ib_r = np.r_[0.0, ib_c[1:] / ib_c[:-1] - 1]
    mats = {s: np.full((len(stocks), T), np.nan) for s in SETUPS}
    inv = {s: np.full((len(stocks), T), np.nan) for s in SETUPS}
    for si, (tk, d) in enumerate(stocks.items()):
        cols = np.array([idx.get(day, -1) for day in d["day"]])
        ok = cols >= 0
        r = np.r_[np.nan, d["c"][1:] / d["c"][:-1] - 1]
        cdi_days = np.array([cdi.get(int(day), 0.0) for day in d["day"]])
        for s in SETUPS:
            pr = daily_returns(d, s)
            daily = np.where(np.isfinite(pr), pr, np.where(np.isfinite(r), cdi_days, np.nan))
            mats[s][si, cols[ok]] = daily[ok]
            inv[s][si, cols[ok]] = np.where(np.isfinite(r[ok]), np.isfinite(pr[ok]).astype(float), np.nan)
    out = {}
    for start_year in (2005, 2016):
        k0 = next(k for k, day in enumerate(cal) if day >= dt.datetime(start_year, 1, 1, tzinfo=dt.timezone.utc).timestamp() // 86400)
        sl = slice(k0, T)
        row = {"CDI": C.stats(cdi_r[sl], cal[sl]), "Ibovespa": C.stats(ib_r[sl], cal[sl])}
        for s in SETUPS:
            row[s] = dict(C.stats(np.nan_to_num(np.nanmean(mats[s][:, sl], axis=0)), cal[sl]),
                          investido=round(float(np.nanmean(inv[s][:, sl])) * 100, 1))
        out[str(start_year)] = row
        print(f"\n== Desde {start_year}; carteira de peso igual, fora da posicao no CDI; sem IR")
        print(f"   {'carteira':<24} {'ao ano':>8} {'queda max':>10} {'investido':>10}")
        for name, s_ in sorted(row.items(), key=lambda kv: -kv[1]["cagr"]):
            inv_s = f"{s_['investido']:>9.1f}%" if "investido" in s_ else ""
            print(f"   {name:<24} {s_['cagr']:>7.2f}% {s_['maxdd']:>9.1f}% {inv_s}")
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "compare_palex_b3.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
