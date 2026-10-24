"""9.x na B3 contra comprar-e-segurar, Ibovespa e CDI (2026-10-24). So le dados publicos.

Uso: python compare_b3.py  -> data/compare_b3.json e tabela na tela.

Carteiras de peso igual entre as acoes disponiveis em cada dia (rebalanceamento diario, uma simplificacao):
  - 9.1 com congruencia semanal e 9.2 com semanal+SMA200: uma posicao por vez em cada acao (regras do livro:
    ordem stop, stop do livro, saida pela MME9); fora da posicao o dinheiro rende o CDI;
  - comprar e segurar as mesmas acoes; Ibovespa (^BVSP); CDI (BCB, serie SGS 12).
Custos: 0,05% por lado nas operacoes; imposto de renda NAO incluido (15% sobre ganhos em swing trade).
Vies de sobrevivencia: so acoes que estao no Ibovespa hoje (favorece o comprar-e-segurar e o 9.x igualmente).
"""
import datetime as dt
import json
import os
import urllib.request

import numpy as np

import check_9x_b3 as B
import check_9x_fiel as F

HERE = os.path.dirname(os.path.abspath(__file__))


def cdi_daily():
    """Taxa diaria do CDI (fracao) por dia (epoch//86400), em janelas de ate 10 anos."""
    path = os.path.join(B.CACHE, "_cdi.json")
    if os.path.exists(path):
        return {int(k): v for k, v in json.load(open(path)).items()}
    out = {}
    for y0 in range(2000, dt.date.today().year + 1, 9):
        y1 = min(y0 + 8, dt.date.today().year)
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json"
               f"&dataInicial=01/01/{y0}&dataFinal=31/12/{y1}")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
            for row in json.load(r):
                d = dt.datetime.strptime(row["data"], "%d/%m/%Y").replace(tzinfo=dt.timezone.utc)
                out[int(d.timestamp()) // 86400] = float(row["valor"]) / 100
    json.dump(out, open(path, "w"))
    return out


def ibov():
    path = os.path.join(B.CACHE, "_BVSP.json")
    if not os.path.exists(path):
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?period1=946684800&period2=9999999999&interval=1d"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            res = json.load(r)["chart"]["result"][0]
        json.dump(dict(t=res["timestamp"], c=res["indicators"]["quote"][0]["close"]), open(path, "w"))
    raw = json.load(open(path))
    return {int(t) // 86400: c for t, c in zip(raw["t"], raw["c"]) if c}


def positions(d, setup, filt):
    """Retorno diario da acao com a regra (uma posicao por vez); NaN = fora da posicao."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    n = len(c)
    e9 = F.R.ema(c, 9)
    up = np.r_[False, e9[1:] > e9[:-1]]
    dn = np.r_[False, e9[1:] < e9[:-1]]
    wk = F.weekly_up(d)
    s200 = F.R.sma(c, 200)
    ret = np.full(n, np.nan)
    busy_until = -1
    for sig in F.signals(d, up, dn):
        i, st, side, trig, stop, lowers = sig
        if st != setup or side != 1 or i <= busy_until or wk[i] != 1:
            continue
        if filt == "semanal+SMA200" and not c[i] > s200[i]:
            continue
        j, entry = i + 1, None
        while j < n and j - i <= 40:  # ordem pendente (mesma logica do check_9x_b3.walk)
            if not up[j - 1]:
                break
            if h[j] >= trig:
                entry = max(o[j], trig)
                break
            if lowers and h[j] < trig:
                trig, stop = h[j], l[j]
            j += 1
        if entry is None or entry <= stop:
            continue
        e, exit_level, x, px = j, None, None, None
        while j < n:
            if l[j] <= stop:
                x, px = j, (min(o[j], stop) if j > e else stop)
                break
            if exit_level is not None and j > e and l[j] <= exit_level:
                x, px = j, min(o[j], exit_level)
                break
            if dn[j] and up[j - 1]:
                exit_level = l[j]
            elif up[j] and exit_level is not None:
                exit_level = None
            j += 1
        if x is None:
            x, px = n - 1, c[-1]
        for k in range(e, x + 1):
            prev = entry if k == e else c[k - 1]
            cur = px if k == x else c[k]
            r = cur / prev - 1
            if k == e:
                r -= B.COST_PER_SIDE
            if k == x:
                r -= B.COST_PER_SIDE
            ret[k] = r
        busy_until = x
    return ret


def stats(daily, days):
    eq = np.cumprod(1 + daily)
    yrs = len(daily) / 248
    peak = np.maximum.accumulate(eq)
    return dict(cagr=round((eq[-1] ** (1 / yrs) - 1) * 100, 2), total=round((eq[-1] - 1) * 100, 1),
                vol=round(daily.std() * np.sqrt(248) * 100, 1), maxdd=round(((eq / peak) - 1).min() * 100, 1),
                start=dt.datetime.fromtimestamp(days[0] * 86400, dt.timezone.utc).strftime("%Y-%m-%d"),
                end=dt.datetime.fromtimestamp(days[-1] * 86400, dt.timezone.utc).strftime("%Y-%m-%d"))


def main():
    cdi = cdi_daily()
    ib = ibov()
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
    bh = np.full((len(stocks), T), np.nan)
    strat = {k: np.full((len(stocks), T), np.nan) for k in ("9.1 semanal", "9.2 semanal+SMA200")}
    invested = {k: np.full((len(stocks), T), np.nan) for k in strat}
    for s, (tk, d) in enumerate(stocks.items()):
        cols = np.array([idx.get(day, -1) for day in d["day"]])
        ok = cols >= 0
        r = np.r_[np.nan, d["c"][1:] / d["c"][:-1] - 1]
        bh[s, cols[ok]] = r[ok]
        cdi_days = np.array([cdi.get(int(day), 0.0) for day in d["day"]])
        for name, (setup, filt) in (("9.1 semanal", ("9.1", "semanal")), ("9.2 semanal+SMA200", ("9.2", "semanal+SMA200"))):
            pr = positions(d, setup, filt)
            # na posicao: retorno da acao; listada e fora da posicao: CDI; antes de listar: NaN
            daily = np.where(np.isfinite(pr), pr, np.where(np.isfinite(r), cdi_days, np.nan))
            strat[name][s, cols[ok]] = daily[ok]
            invested[name][s, cols[ok]] = np.where(np.isfinite(r[ok]), np.isfinite(pr[ok]).astype(float), np.nan)
    results = {}
    for start_year in (2005, 2016):
        k0 = next(k for k, day in enumerate(cal) if day >= (dt.datetime(start_year, 1, 1, tzinfo=dt.timezone.utc).timestamp() // 86400))
        sl = slice(k0, T)
        row = {}
        row["CDI"] = stats(cdi_r[sl], cal[sl])
        row["Ibovespa"] = stats(ib_r[sl], cal[sl])
        row["Comprar e segurar (59 acoes, peso igual)"] = stats(np.nan_to_num(np.nanmean(bh[:, sl], axis=0)), cal[sl])
        for name, m in strat.items():
            row[f"{name} (fora da posicao no CDI)"] = dict(stats(np.nan_to_num(np.nanmean(m[:, sl], axis=0)), cal[sl]),
                                                          investido=round(float(np.nanmean(invested[name][:, sl])) * 100, 1))
        results[str(start_year)] = row
        print(f"\n== Desde {start_year} (ate {row['CDI']['end']}); sem imposto de renda")
        print(f"   {'carteira':<48} {'ao ano':>8} {'total':>9} {'volat.':>7} {'queda max':>10}")
        for name, s in row.items():
            extra = f"  (investido {s['investido']}% do tempo)" if "investido" in s else ""
            print(f"   {name:<48} {s['cagr']:>7.2f}% {s['total']:>8.0f}% {s['vol']:>6.1f}% {s['maxdd']:>9.1f}%{extra}")
    json.dump(results, open(os.path.join(HERE, "data", "compare_b3.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
