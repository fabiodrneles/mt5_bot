"""Teste justo do 9.x em ACOES DA B3, o mercado do Palex (2026-10-24).

So le dados publicos (API de graficos do Yahoo Finance, tickers .SA); nenhuma ordem.
Uso: python check_9x_b3.py [--refresh]  -> data/b3/*.json (cache), data/9x_b3.json e resumo na tela.

Mesmas regras do check_9x_fiel.py (livro do Palex): grafico diario, ordem stop acima da maxima, stop do livro,
saida conduzida pela MME9 (e alvo de 2x so para comparar). Diferencas de mercado:
  - precos ajustados por desdobramentos e proventos (fator adjclose/close aplicado a O/H/L), para nao criar
    gaps falsos nos candles;
  - custos de acao a vista: 0,05% por lado (emolumentos/liquidacao da B3 ~0,03% + spread/slippage),
    corretagem zero (padrao das corretoras de varejo hoje) e SEM swap; imposto de renda nao incluido;
  - universo: acoes liquidas atuais do Ibovespa -> ha VIES DE SOBREVIVENCIA (empresas que sairam do indice ou
    quebraram nao estao aqui), o que favorece o resultado.
"""
import json
import os
import sys
import time
import urllib.request

import numpy as np

import check_9x_fiel as F

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "b3")
COST_PER_SIDE = 0.0005
SPLIT = 0.6
TICKERS = ["PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "ABEV3", "WEGE3", "B3SA3", "RENT3", "SUZB3",
           "ITSA4", "LREN3", "GGBR4", "JBSS3", "RADL3", "EQTL3", "CSNA3", "PRIO3", "VIVT3", "SBSP3",
           "TOTS3", "BBSE3", "CMIG4", "UGPA3", "EMBR3", "CPLE6", "KLBN11", "MGLU3", "CSAN3", "ENEV3",
           "GOAU4", "USIM5", "TIMS3", "EGIE3", "CYRE3", "MULT3", "HYPE3", "FLRY3", "BRKM5", "CPFE3",
           "TAEE11", "ENGI11", "SANB11", "BPAC11", "ASAI3", "VBBR3", "RDOR3", "SLCE3", "ALPA4", "PETR3",
           "BBDC3", "ELET3", "ELET6", "RAIL3", "AZUL4", "CCRO3", "MRFG3", "BRFS3", "IGTI11", "EZTC3",
           "MRVE3", "YDUQ3", "COGN3", "PCAR3", "CMIN3", "RRRP3", "SMTO3", "ARZZ3", "POSI3", "QUAL3"]


def fetch(ticker, refresh=False):
    path = os.path.join(CACHE, f"{ticker}.json")
    if os.path.exists(path) and not refresh:
        return json.load(open(path))
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA"
           "?period1=946684800&period2=9999999999&interval=1d&events=div%2Csplit")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.load(resp)
    except Exception as exc:  # ticker inexistente/renomeado: segue sem ele
        print(f"  {ticker}: sem dados ({exc})", flush=True)
        return None
    res = (raw.get("chart", {}).get("result") or [None])[0]
    if not res or "timestamp" not in res:
        return None
    q = res["indicators"]["quote"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    data = dict(t=res["timestamp"], o=q["open"], h=q["high"], l=q["low"], c=q["close"], adj=adj)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(data, open(path, "w"))
    time.sleep(0.5)  # gentil com a API publica
    return data


def to_arrays(raw):
    """Arrays limpos e ajustados por proventos; descarta dias sem negocio ou com OHLC inconsistente."""
    cols = [np.array([np.nan if v is None else v for v in raw[k]], float) for k in ("o", "h", "l", "c")]
    t = np.array(raw["t"], np.int64)
    adj = np.array([np.nan if v is None else v for v in (raw["adj"] or raw["c"])], float)
    o, h, l, c = cols
    ok = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c) & np.isfinite(adj) & (c > 0) & (h >= l)
    o, h, l, c, t, adj = o[ok], h[ok], l[ok], c[ok], t[ok], adj[ok]
    f = adj / c
    o, h, l, c = o * f, h * f, l * f, adj
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    day = t // 86400  # o timestamp diario do Yahoo cai no meio do pregao: o dia UTC e o dia do pregao
    return dict(t=t, o=o, h=h, l=l, c=c, day=day, spr=np.zeros(len(c)))


def walk(d, up, dn, sig, exit_mode):
    """Como check_9x_fiel.walk, mas com custo percentual de acao a vista e sem swap. Devolve R ou None."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    i, setup, side, trig, stop, lowers = sig
    n = len(c)
    trend = up if side > 0 else dn
    j, entry = i + 1, None
    while j < n:
        if not trend[j - 1]:
            return None
        if (h[j] >= trig) if side > 0 else (l[j] <= trig):
            entry = max(o[j], trig) if side > 0 else min(o[j], trig)
            break
        if lowers:
            if side > 0 and h[j] < trig:
                trig, stop = h[j], l[j]
            if side < 0 and l[j] > trig:
                trig, stop = l[j], h[j]
        j += 1
        if j - i > 40:
            return None
    if entry is None:
        return None
    risk = (entry - stop) if side > 0 else (stop - entry)
    if risk <= 0:
        return None
    e, exit_level, exit_px = j, None, None
    target = entry + side * 2 * risk
    while j < n:
        if side > 0:
            if l[j] <= stop:
                exit_px = min(o[j], stop) if j > e else stop
                break
            if exit_level is not None and j > e and l[j] <= exit_level:
                exit_px = min(o[j], exit_level)
                break
            if exit_mode == "alvo2x" and h[j] >= target:
                exit_px = max(o[j], target) if j > e else target
                break
        else:
            if h[j] >= stop:
                exit_px = max(o[j], stop) if j > e else stop
                break
            if exit_level is not None and j > e and h[j] >= exit_level:
                exit_px = max(o[j], exit_level)
                break
            if exit_mode == "alvo2x" and l[j] <= target:
                exit_px = min(o[j], target) if j > e else target
                break
        if exit_mode == "mme9":
            turned = (dn[j] and up[j - 1]) if side > 0 else (up[j] and dn[j - 1])
            back = up[j] if side > 0 else dn[j]
            if turned:
                exit_level = l[j] if side > 0 else h[j]
            elif back and exit_level is not None:
                exit_level = None
        j += 1
    if exit_px is None:
        return None
    cost = COST_PER_SIDE * (entry + exit_px)
    return (side * (exit_px - entry) - cost) / (risk + COST_PER_SIDE * entry), j - e + 1


def main():
    refresh = "--refresh" in sys.argv
    trades = []
    used = []
    for tk in TICKERS:
        raw = fetch(tk, refresh)
        if not raw:
            continue
        d = to_arrays(raw)
        if len(d["c"]) < 500:
            continue
        used.append((tk, len(d["c"])))
        e9 = F.R.ema(d["c"], 9)
        up = np.r_[False, e9[1:] > e9[:-1]]
        dn = np.r_[False, e9[1:] < e9[:-1]]
        wk = F.weekly_up(d)
        s200 = F.R.sma(d["c"], 200)
        cut = d["t"][int(len(d["t"]) * SPLIT)]
        for sig in F.signals(d, up, dn):
            i, setup, side = sig[0], sig[1], sig[2]
            res = {m: walk(d, up, dn, sig, m) for m in ("mme9", "alvo2x")}
            if all(v is None for v in res.values()):
                continue
            trades.append(dict(tk=tk, setup=setup, side=side, oos=bool(d["t"][i] >= cut),
                               year=int(1970 + d["t"][i] // 31557600),
                               cong=bool((wk[i] == 1) if side > 0 else (wk[i] == 0)),
                               s200=bool((d["c"][i] > s200[i]) if side > 0 else (d["c"][i] < s200[i])),
                               **{m: list(v) for m, v in res.items() if v is not None}))
    json.dump(dict(used=used, trades=trades), open(os.path.join(HERE, "data", "9x_b3.json"), "w"))
    print(f"acoes com dados: {len(used)} | anos medios: {np.mean([n for _, n in used]) / 248:.1f} | sinais acionados: {len(trades)}")

    def st(rs):
        a = np.array(rs)
        if len(a) < 10:
            return f"{len(a):5d} tr"
        t = a.mean() / a.std(ddof=1) * np.sqrt(len(a))
        return (f"{len(a):5d} tr {a.mean():+.3f} R  acerto {np.mean(a > 0) * 100:4.0f}%  t {t:+5.2f}  "
                f"ganho {a[a > 0].mean():.2f} perda {a[a <= 0].mean():.2f}")
    for side_name, sides in (("COMPRA", (1,)), ("COMPRA+VENDA", (1, -1))):
        print(f"\n== {side_name}")
        for setup in F.SETUPS:
            for filt in ("nenhum", "semanal", "semanal+SMA200"):
                for mode in ("mme9", "alvo2x"):
                    sel = [x for x in trades if x["setup"] == setup and x["side"] in sides and mode in x
                           and (filt == "nenhum" or x["cong"]) and (filt != "semanal+SMA200" or x["s200"])]
                    i_ = [x[mode][0] for x in sel if not x["oos"]]
                    o_ = [x[mode][0] for x in sel if x["oos"]]
                    print(f"  {setup} {filt:<15} {mode:<6} IS {st(i_)} || OOS {st(o_)}")


if __name__ == "__main__":
    main()
