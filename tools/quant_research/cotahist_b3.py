"""Setups na B3 com a SERIE HISTORICA OFICIAL (COTAHIST), sem vies de sobrevivencia (2026-10-24).

So le dados publicos da B3. Uso: python cotahist_b3.py  -> data/cotahist/*.ZIP (cache), data/cotahist_b3.json.

Diferencas em relacao ao compare_palex_b3.py (dados do Yahoo, so as acoes que estao no Ibovespa hoje):
  - TODAS as acoes negociadas em cada ano, inclusive as que depois sairam da bolsa, faliram ou foram compradas;
  - universo PONTO-NO-TEMPO: em cada ano, as 60 acoes mais negociadas (volume financeiro) no ANO ANTERIOR;
  - precos oficiais sem ajuste de proventos (conservador para as compras); desdobramentos e grupamentos
    detectados pelo salto fechamento->abertura proximo de fracoes simples (2, 3, 4, 5, 8, 10, 20, 50, 100 e
    inversas, tolerancia de 3%), e saltos acima de 3x ou abaixo de 0,2x (grupamentos e a mudanca de cotacao
    por lote de mil para por acao, comuns ate 2007), ajustados para tras. Quedas reais (ex.: -77% da
    Americanas em jan/2023) nao sao confundidas com desdobramento.
Carteiras como no compare_palex_b3.py: peso igual entre os membros do universo no dia, uma posicao por vez por
acao, fora da posicao no CDI, custo 0,05% por lado, sem imposto de renda.
"""
import datetime as dt
import io
import json
import os
import urllib.request
import zipfile

import numpy as np

import compare_b3 as C
import compare_palex_b3 as CP

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "cotahist")
YEARS = range(2004, dt.date.today().year + 1)
TOP_N = 60
FRACTIONS = sorted({k for k in (2, 3, 4, 5, 8, 10, 20, 50, 100)} | {1 / k for k in (2, 3, 4, 5, 8, 10, 20, 50, 100)})


def download(year):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"COTAHIST_A{year}.ZIP")
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        url = f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(path + ".tmp", "wb") as f:
            f.write(r.read())
        os.replace(path + ".tmp", path)
        print(f"  baixado {year}: {os.path.getsize(path) / 1e6:.0f} MB", flush=True)
    return path


def parse(path):
    """Linhas do mercado a vista, lote padrao (layout oficial do COTAHIST)."""
    rows = []
    with zipfile.ZipFile(path) as z:
        with z.open(z.namelist()[0]) as raw:
            for line in io.TextIOWrapper(raw, encoding="latin-1"):
                if line[0:2] != "01" or line[10:12] != "02" or line[24:27] != "010":
                    continue
                fat = int(line[210:217] or 1) or 1
                rows.append((line[12:24].strip(), int(line[2:10]),
                             int(line[56:69]) / 100 / fat, int(line[69:82]) / 100 / fat,
                             int(line[82:95]) / 100 / fat, int(line[108:121]) / 100 / fat,
                             int(line[170:188]) / 100))
    return rows


def load_all():
    npz = os.path.join(CACHE, "b3_vista.npz")
    if os.path.exists(npz):
        z = np.load(npz, allow_pickle=True)
        return {k: z[k] for k in z.files}
    rows = []
    for y in YEARS:
        rows += parse(download(y))
    tk = np.array([r[0] for r in rows])
    data = dict(tk=tk, date=np.array([r[1] for r in rows]), o=np.array([r[2] for r in rows]),
                h=np.array([r[3] for r in rows]), l=np.array([r[4] for r in rows]),
                c=np.array([r[5] for r in rows]), vol=np.array([r[6] for r in rows]))
    np.savez_compressed(npz, **data)
    return data


def split_adjust(o, h, l, c):
    """Ajusta desdobramentos/grupamentos para tras. Devolve arrays ajustados e a lista de eventos."""
    o, h, l, c = o.copy(), h.copy(), l.copy(), c.copy()
    events = []
    for t in range(1, len(c)):
        if c[t - 1] <= 0 or o[t] <= 0:
            continue
        r = o[t] / c[t - 1]
        if 0.62 < r < 1.6:
            continue
        if r > 3 or r < 0.2:
            # Grupamento ou mudanca de cotacao por lote de mil -> por acao (fatores de 1.000 a 50.000 nos
            # anos 2000): nenhuma acao liquida multiplica por 3 de um dia para o outro (ex.: PRIO3 jun/2016 4,5x, BRPR3 ago/2023 4,3x). Ajuste pelo fator exato.
            f = r
        else:
            f = min(FRACTIONS, key=lambda x: abs(np.log(r / x)))
        if f == r or abs(np.log(r / f)) < 0.03:
            o[:t] *= f
            h[:t] *= f
            l[:t] *= f
            c[:t] *= f
            events.append((t, round(f, 4)))
    return o, h, l, c, events


def series(data):
    out = {}
    order = np.lexsort((data["date"], data["tk"]))
    tk, date = data["tk"][order], data["date"][order]
    bounds = np.flatnonzero(np.r_[True, tk[1:] != tk[:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 250:
            continue
        sl = order[a:b]
        days = np.array([dt.datetime.strptime(str(x), "%Y%m%d").replace(tzinfo=dt.timezone.utc).timestamp()
                         for x in date[a:b]]).astype(np.int64)
        o, h, l, c = data["o"][sl], data["h"][sl], data["l"][sl], data["c"][sl]
        # Dia de negocio unico (maxima = minima) com salto > 30%: cotacao isolada de papel iliquido, nao
        # executavel (ex.: PCAR3 em 2009 e 2017). Descartado.
        prev = np.r_[c[:1], c[:-1]]
        keep = ~((h == l) & (np.abs(o / np.where(prev > 0, prev, 1) - 1) > 0.3))
        sl, days = sl[keep], days[keep]
        o, h, l, c, ev = split_adjust(o[keep], h[keep], l[keep], c[keep])
        h = np.maximum.reduce([h, o, c])
        l = np.minimum.reduce([l, o, c])
        out[str(tk[a])] = dict(t=days, day=days // 86400, o=o, h=h, l=l, c=c, vol=data["vol"][sl],
                               spr=np.zeros(len(c)), splits=ev)
    return out


def universe(stocks):
    """Ano -> conjunto das TOP_N acoes por volume financeiro no ano anterior (ponto-no-tempo)."""
    vol_by_year = {}
    for tk, d in stocks.items():
        years = (d["t"].astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970)
        for y in np.unique(years):
            vol_by_year.setdefault(int(y), {})[tk] = float(d["vol"][years == y].sum())
    uni = {}
    for y in YEARS:
        prev = vol_by_year.get(y - 1, {})
        uni[y] = set(sorted(prev, key=prev.get, reverse=True)[:TOP_N])
    return uni


def main():
    data = load_all()
    stocks = series(data)
    uni = universe(stocks)
    members = set().union(*uni.values())
    stocks = {k: v for k, v in stocks.items() if k in members}
    print(f"acoes que passaram pelo universo (top {TOP_N} por ano): {len(stocks)}; "
          f"desdobramentos ajustados: {sum(len(d['splits']) for d in stocks.values())}")
    cdi, ib = C.cdi_daily(), C.ibov()
    cal = sorted(set().union(*[set(d["day"].tolist()) for d in stocks.values()]) & set(cdi) & set(ib))
    idx = {day: k for k, day in enumerate(cal)}
    T = len(cal)
    cal_year = np.array([dt.datetime.fromtimestamp(day * 86400, dt.timezone.utc).year for day in cal])
    cdi_r = np.array([cdi[day] for day in cal])
    ib_c = np.array([ib[day] for day in cal])
    ib_r = np.r_[0.0, ib_c[1:] / ib_c[:-1] - 1]
    # Todos os setups de compra no diario: os 11 do palex_setups.py e a familia 9.x (regras do livro).
    names = list(CP.SETUPS) + ["9.1 semanal", "9.2 semanal+SMA200", "9.3 semanal+SMA200", "9.4 semanal",
                               "IFR2 Stormer <25", "IFR2 Stormer <25 +MM200", "IFR2 Stormer <10", "IFR2 Stormer <10 +MM200"]
    if os.environ.get("ONLY"):
        names = [n for n in names if os.environ["ONLY"] in n]
    bh = np.full((len(stocks), T), np.nan)
    mats = {s: np.full((len(stocks), T), np.nan) for s in names}
    for si, (tk, d) in enumerate(stocks.items()):
        cols = np.array([idx.get(int(day), -1) for day in d["day"]])
        ok = cols >= 0
        member = np.array([tk in uni.get(int(cal_year[k]), set()) for k in cols[ok]])
        r = np.r_[np.nan, d["c"][1:] / d["c"][:-1] - 1]
        cdi_days = np.array([cdi.get(int(day), 0.0) for day in d["day"]])
        bh[si, cols[ok]] = np.where(member, r[ok], np.nan)
        for s in names:
            if s.startswith("9."):
                setup, filt = s.split(" ", 1)
                pr = C.positions(d, setup, filt)
            else:
                pr = CP.daily_returns(d, s)
            daily = np.where(np.isfinite(pr), pr, np.where(np.isfinite(r), cdi_days, np.nan))
            mats[s][si, cols[ok]] = np.where(member, daily[ok], np.nan)

    def met(rr, c):
        eq = np.cumprod(1 + rr)
        ex = rr - c
        return dict(cagr=round((eq[-1] ** (248 / len(rr)) - 1) * 100, 2),
                    sharpe=round(float(ex.mean() / ex.std() * np.sqrt(248)), 2) if ex.std() > 0 else 0.0,
                    maxdd=round(float(((eq / np.maximum.accumulate(eq)) - 1).min() * 100), 1))
    results = {}
    for y0 in (2005, 2016):
        k0 = int(np.argmax(cal_year >= y0))
        sl = slice(k0, T)
        c = cdi_r[sl]
        ew = np.nan_to_num(np.nanmean(bh[:, sl], axis=0))
        rows = {"CDI": met(c, c), "Ibovespa": met(ib_r[sl], c), "Comprar e segurar (universo ponto-no-tempo)": met(ew, c),
                "Mistura fixa 55% acoes + 45% CDI": met(0.55 * ew + 0.45 * c, c)}
        for s in names:
            rows[s] = met(np.nan_to_num(np.nanmean(mats[s][:, sl], axis=0)), c)
        results[str(y0)] = rows
        print(f"\n== Desde {y0} (universo sem sobrevivencia; sem IR): ao ano | Sharpe acima do CDI | queda maxima")
        for k, v in rows.items():
            print(f"   {k:<46} {v['cagr']:6.2f}%   Sharpe {v['sharpe']:5.2f}   queda {v['maxdd']:6.1f}%")
    out = f"cotahist_b3_{os.environ['ONLY'].replace(' ', '_')}.json" if os.environ.get("ONLY") else "cotahist_b3.json"
    json.dump(dict(stocks=len(stocks), results=results), open(os.path.join(HERE, "data", out), "w"), indent=1)


if __name__ == "__main__":
    main()
