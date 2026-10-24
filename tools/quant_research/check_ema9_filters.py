"""Regra do dono, versao 2 (2026-10-24): cruzamento da MME9 com stop na maxima/minima do candle do sinal,
alvo 2x essa distancia, e FILTROS de volume e tendencia para so entrar nos sinais "bons".

So le historico. Uso: python check_ema9_filters.py SYM TF [AAAA-MM-DD]
1. Mostra, no dia pedido, cada sinal com volume relativo, tendencia e resultado.
2. Testa todas as combinacoes de filtro; o filtro e ESCOLHIDO so nos 60% iniciais (IS) e MEDIDO nos 40%
   finais (OOS). Imprime o numero de combinacoes testadas (para o leitor descontar a sorte).
"""
import datetime as dt
import itertools
import sys

import numpy as np

import research2 as R


def features(d):
    c, o, v = d["c"], d["o"], d["v"]
    e9, e20, e50 = R.ema(c, 9), R.ema(c, 20), R.ema(c, 50)
    s200 = R.sma(c, 200)
    vrel = v / R.lag(R.sma(v, 20))                     # volume do candle / media dos 20 anteriores
    ax, pdi, ndi = R.adx(d, 14)
    sell = (c < o) & (c < e9) & (R.lag((c > e9).astype(float)) == 1)
    buy = (c > o) & (c > e9) & (R.lag((c < e9).astype(float)) == 1)
    out = dict(e9=e9, e20=e20, e50=e50, s200=s200, vrel=vrel, adx=ax, pdi=pdi, ndi=ndi, sell=sell, buy=buy)
    for name, secs in (("M30", 1800), ("H1", 3600), ("H4", 14400)):
        out["up_" + name] = htf_trend(d, secs)
    return out


def htf_trend(d, secs):
    """Tendencia num timeframe maior (MME9 > MME21), usando SO o candle maior ja FECHADO no fechamento
    do candle atual. Sem isso o teste veria o futuro (look-ahead)."""
    t, c = d["t"], d["c"]
    bar = int(np.median(np.diff(t)))
    key = t // secs
    last = np.r_[key[1:] != key[:-1], True]          # ultimo candle pequeno de cada candle maior
    hk, hc = key[last], c[last]
    up = (R.ema(hc, 9) > R.ema(hc, 21)).astype(float)
    # candle maior completo mais recente no fechamento do candle i: chave (t+bar)//secs - 1
    done = (t + bar) // secs - 1
    pos = np.searchsorted(hk, done, side="right") - 1
    res = np.where(pos >= 0, up[np.clip(pos, 0, None)], np.nan)
    return np.where(np.isnan(res), 0.5, res)          # 1 = alta, 0 = baixa, 0.5 = sem dado


TREND = {
    "nenhum": lambda f, c: (np.ones(len(c), bool), np.ones(len(c), bool)),
    "EMA20/50": lambda f, c: (f["e20"] > f["e50"], f["e20"] < f["e50"]),
    "SMA200": lambda f, c: (c > f["s200"], c < f["s200"]),
    "ADX>20+DMI": lambda f, c: ((f["adx"] > 20) & (f["pdi"] > f["ndi"]), (f["adx"] > 20) & (f["ndi"] > f["pdi"])),
    "ADX>25+DMI": lambda f, c: ((f["adx"] > 25) & (f["pdi"] > f["ndi"]), (f["adx"] > 25) & (f["ndi"] > f["pdi"])),
    "EMA20/50+ADX>20": lambda f, c: ((f["e20"] > f["e50"]) & (f["adx"] > 20), (f["e20"] < f["e50"]) & (f["adx"] > 20)),
    # Alinhamento multi-tempo (pedido do dono): os candles maiores ja fechados apontam para o mesmo lado.
    "MTF H1": lambda f, c: (f["up_H1"] == 1, f["up_H1"] == 0),
    "MTF M30+H1": lambda f, c: ((f["up_M30"] == 1) & (f["up_H1"] == 1), (f["up_M30"] == 0) & (f["up_H1"] == 0)),
    "MTF M30+H1+H4": lambda f, c: ((f["up_M30"] == 1) & (f["up_H1"] == 1) & (f["up_H4"] == 1),
                                   (f["up_M30"] == 0) & (f["up_H1"] == 0) & (f["up_H4"] == 0)),
}
VOL = (0.0, 1.0, 1.5, 2.0, 3.0)


def run_rule(sym, d, f, vmin, trend, side, R_mult=2.0):
    c, h, l, o = d["c"], d["h"], d["l"], d["o"]
    up_ok, dn_ok = TREND[trend](f, c)
    vok = np.nan_to_num(f["vrel"]) >= vmin
    sig = np.zeros(len(c), int)
    if side in ("ambos", "compra"):
        sig[f["buy"] & up_ok & vok] = 1
    if side in ("ambos", "venda"):
        sig[f["sell"] & dn_ok & vok] = -1
    # stop na minima (compra) / maxima (venda) do candle do sinal, medido a partir da abertura seguinte
    nxt_o = np.r_[o[1:], np.nan]
    dist = np.where(sig > 0, nxt_o - l, np.where(sig < 0, h - nxt_o, np.nan))
    sig[~(dist > 0)] = 0
    return R.simulate(sym, d, sig, dist, R_mult * dist, None, None, 10 ** 6, False), sig, dist


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    day = sys.argv[3] if len(sys.argv) > 3 else None
    d = R.load(sym, tf)
    f = features(d)
    cut = d["t"][int(len(d["t"]) * R.SPLIT)]
    if day:
        d0 = int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp()) // 86400
        _, sig, dist = run_rule(sym, d, f, 0.0, "nenhum", "ambos")
        print(f"Sinais em {day} (stop na maxima/minima do candle, alvo 2x):")
        print("  hora   lado    vol/media  EMA20>50  SMA200  ADX   DI     resultado")
        for i in np.flatnonzero((d["day"] == d0) & (sig != 0)):
            one = np.zeros_like(sig)
            one[i] = sig[i]
            tr = R.simulate(sym, d, one, dist, 2 * dist, None, None, 10 ** 6, False)
            res = f"${tr[0, 2]:+.2f} ({'ALVO' if tr[0, 2] > 0 else 'stop'})" if len(tr) else "sem entrada"
            hh = dt.datetime.fromtimestamp(int(d["t"][i]), dt.timezone.utc).strftime("%H:%M")
            print(f"  {hh}  {'VENDA ' if sig[i] < 0 else 'COMPRA'}  {f['vrel'][i]:8.2f}  "
                  f"{'sim' if f['e20'][i] > f['e50'][i] else 'nao':>8}  {'acima' if d['c'][i] > f['s200'][i] else 'abaixo':>6}  "
                  f"{f['adx'][i]:4.0f}  {'+DI' if f['pdi'][i] > f['ndi'][i] else '-DI':>3}   {res}")
    rows = []
    for vmin, trend, side in itertools.product(VOL, TREND, ("ambos", "venda", "compra")):
        tr, _, _ = run_rule(sym, d, f, vmin, trend, side)
        ins, oos = tr[tr[:, 0] < cut], tr[tr[:, 0] >= cut]
        rows.append((vmin, trend, side, R.stats(ins), R.stats(oos)))
    print(f"\n{sym} {tf}: {len(rows)} combinacoes de filtro testadas. Melhores pelo IS (t do lucro por trade):")
    print("  vol>=  tendencia          lado    | IS: trades acerto  lucro    t   | OOS: trades acerto  lucro    t")
    eligible = [r for r in rows if r[3]["n"] >= 30]
    for vmin, trend, side, i, o in sorted(eligible, key=lambda r: -r[3]["t"])[:12]:
        print(f"  {vmin:4.1f}  {trend:<17} {side:<7} | {i['n']:5d} {i['wr']:5.1f}% {i['net']:+7.2f} {i['t']:+5.2f} | "
              f"{o['n']:5d} {o['wr']:5.1f}% {o['net']:+7.2f} {o['t']:+5.2f}")
    pos_both = sum(1 for r in eligible if r[3]["net"] > 0 and r[4]["net"] > 0)
    print(f"\nCombinacoes com lucro no IS e no OOS: {pos_both} de {len(eligible)}")
    best = max(eligible, key=lambda r: r[3]["t"])
    print(f"Escolhida pelo IS: vol>={best[0]} {best[1]} {best[2]} -> OOS {best[4]['n']} trades, "
          f"lucro ${best[4]['net']:+.2f}, t {best[4]['t']:+.2f}")


if __name__ == "__main__":
    main()
