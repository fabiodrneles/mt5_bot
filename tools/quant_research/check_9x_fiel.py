"""Teste justo do 9.x (2026-10-24): as regras do livro do Palex, como ele opera, no grafico diario.

So le historico. Uso: python check_9x_fiel.py [procs]  -> data/9x_fiel.json e resumo na tela.

Diferencas em relacao a versao simplificada da pesquisa ampla (guia, cap. 14 §14.8):
  - ENTRADA por ordem stop 1 tick acima da maxima do candle de sinal (venda: abaixo da minima). No 9.1 a ordem
    vale enquanto a MME9 nao virar contra; no 9.2/9.3 a entrada desce para as maximas menores enquanto a MME9
    continuar a favor (livro, p. 11 e 14). Sinal que nao e acionado nao vira trade.
  - SAIDA conduzida pela MME9 (livro, p. 10): quando a MME9 vira contra, marca-se a minima do candle que a
    virou; perdendo essa minima, sai. Stop inicial do livro ate la. Para comparar: alvo fixo de 2x o risco.
  - Grafico DIARIO; filtros do livro: congruencia com o semanal (MME9 semanal a favor, so semanas fechadas)
    e a SMA200.
  - Custos: spread, comissao e swap (o resultado sem swap tambem e guardado: acoes a vista na B3 nao pagam swap).
  - CFDs de acoes com abertura diaria irreal (artefato A6 do cap. 14) sao excluidos.
Cada sinal e avaliado sozinho (ordens sobrepostas sao permitidas), em multiplos do risco (R).
"""
import json
import os
import sys

import numpy as np

import research2 as R

SETUPS = ("9.1", "9.2", "9.3", "9.4")


def artifact_open(d):
    """Assinatura do artefato A6: gap medio negativo desfeito pelo corpo (abertura irreal)."""
    gap = d["o"][1:] - d["c"][:-1]
    body = (d["c"] - d["o"])[1:]
    tr = np.mean(d["h"] - d["l"])
    return gap.mean() / tr < -0.05 and body.mean() / tr > 0.05


def weekly_up(d):
    """MME9 semanal subindo, usando so semanas FECHADAS antes do candle (1 = alta, 0 = baixa, nan = sem dado)."""
    wk = (d["day"] + 3) // 7  # semana comecando na segunda
    last = np.r_[wk[1:] != wk[:-1], True]
    wclose, wid = d["c"][last], wk[last]
    e = R.ema(wclose, 9)
    up = np.r_[np.nan, (e[1:] > e[:-1]).astype(float)]
    pos = np.searchsorted(wid, wk, side="left") - 1  # ultima semana completa antes da semana do candle
    return np.where(pos >= 0, up[np.clip(pos, 0, None)], np.nan)


def signals(d, up, dn):
    """(i, setup, lado, gatilho, stop, desce_entrada) no fechamento do candle i."""
    h, l, c = d["h"], d["l"], d["c"]
    n = len(c)
    out = []
    for i in range(3, n - 1):
        # 9.1: MME9 vira
        if dn[i - 1] and up[i]:
            out.append((i, "9.1", 1, h[i], l[i], False))
        if up[i - 1] and dn[i]:
            out.append((i, "9.1", -1, l[i], h[i], False))
        # 9.2: MME9 a favor e o candle FECHA alem da minima/maxima anterior
        if up[i] and up[i - 1] and c[i] < l[i - 1]:
            out.append((i, "9.2", 1, h[i], l[i], True))
        if dn[i] and dn[i - 1] and c[i] > h[i - 1]:
            out.append((i, "9.2", -1, l[i], h[i], True))
        # 9.4: vira contra por 1 candle sem perder a minima e volta
        if up[i - 2] and dn[i - 1] and up[i] and l[i] >= l[i - 1]:
            out.append((i, "9.4", 1, h[i], l[i - 1], False))
        if dn[i - 2] and up[i - 1] and dn[i] and h[i] <= h[i - 1]:
            out.append((i, "9.4", -1, l[i], h[i - 1], False))
        # 9.3: referencia = maior (menor) fechamento da perna + >= 2 fechamentos alem dela, MME9 sem virar
        for side, trend in ((1, up), (-1, dn)):
            for r in range(i - 2, max(i - 12, 0), -1):
                if not trend[r:i + 1].all():
                    break
                after = c[r + 1:i + 1]
                extreme = c[r] > c[r - 1] if side > 0 else c[r] < c[r - 1]
                beyond = (after < c[r]).all() if side > 0 else (after > c[r]).all()
                if extreme and beyond:
                    if side > 0:
                        out.append((i, "9.3", 1, h[i], l[i], True))
                    else:
                        out.append((i, "9.3", -1, l[i], h[i], True))
                    break
    return out


def walk(sym, d, up, dn, sig, exit_mode):
    """Uma ordem stop do sinal ate a saida. Devolve (R com swap, R sem swap, candles) ou None."""
    m = R._meta()[sym]
    o, h, l, c, day = d["o"], d["h"], d["l"], d["c"], d["day"]
    spr, upu, comm = d["spr"], m["usd_per_unit"], m["comm_rt"]
    swap3 = (int(m.get("swap3", 3)) + 6) % 7
    i, setup, side, trig, stop, lowers = sig
    n = len(c)
    trend = up if side > 0 else dn
    j = i + 1
    entry = None
    while j < n:  # ---- ordem pendente
        if not trend[j - 1]:
            return None  # MME9 virou contra antes do acionamento: setup desconfigurado
        hit = h[j] >= trig if side > 0 else l[j] <= trig
        if hit:
            entry = (max(o[j], trig) + spr[j]) if side > 0 else min(o[j], trig)
            break
        if lowers:  # 9.2/9.3: a entrada acompanha as maximas (minimas) menores
            if side > 0 and h[j] < trig:
                trig, stop = h[j], l[j]
            if side < 0 and l[j] > trig:
                trig, stop = l[j], h[j]
        j += 1
        if j - i > 40:
            return None
    if entry is None:
        return None
    risk_px = (entry - stop) if side > 0 else (stop - entry)
    if risk_px <= 0:
        return None
    e = j
    exit_level = None
    exit_px = None
    target = entry + side * 2 * risk_px
    while j < n:  # ---- posicao
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
            if h[j] + spr[j] >= stop:
                exit_px = (max(o[j], stop - spr[j]) if j > e else stop - spr[j])
                break
            if exit_level is not None and j > e and h[j] + spr[j] >= exit_level:
                exit_px = max(o[j], exit_level - spr[j])
                break
            if exit_mode == "alvo2x" and l[j] + spr[j] <= target:
                exit_px = target - spr[j]
                break
        if exit_mode == "mme9":  # conduz pela MME9: marca a minima (maxima) do candle que virou a media
            turned = (dn[j] and up[j - 1]) if side > 0 else (up[j] and dn[j - 1])
            back = up[j] if side > 0 else dn[j]
            if turned:
                exit_level = l[j] if side > 0 else h[j]
            elif back and exit_level is not None:
                exit_level = None  # a media voltou a favor antes de perder a marca
        j += 1
    if exit_px is None:
        return None
    pnl_px = side * (exit_px - entry)
    rolls = R._rollovers(day[e], day[j], swap3)
    s = m["swapL"] if side > 0 else m["swapS"]
    sw = (s * m["point"] * upu if m["swap_mode"] == 1 else entry * s / 100 / 360 * upu) * rolls
    risk_usd = risk_px * upu + comm
    usd_noswap = pnl_px * upu - comm
    return (usd_noswap + sw) / risk_usd, usd_noswap / risk_usd, j - e + 1


def run_symbol(sym):
    try:
        d = R.load(sym, "D1")
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return sym, None
    if len(d["c"]) < 400:
        return sym, None
    m = R._meta()[sym]
    group = m.get("group", "").split()[0]
    cls = ("Acoes" if m.get("group", "").startswith("CFD Stocks") else "Indices" if m.get("group", "").startswith("CFD Indices")
           else "Forex" if group.startswith(("FX", "EURUSD")) else "Cripto" if group == "Crypto" else "Commodities")
    if cls == "Acoes" and artifact_open(d):
        return sym, {"excluded": True, "cls": cls}
    if os.environ.get("SPREAD_NORMAL"):
        # Sensibilidade: ordem stop costuma ser acionada no meio do pregao, com o spread normal (mediana do H1),
        # e nao com o spread da hora de abertura que o D1 cobra por padrao.
        h1 = np.load(os.path.join(R.DATA, f"{sym}_H1.npy"))["spread"]
        pos = h1[h1 > 0]
        d["spr"] = np.full(len(d["c"]), (np.median(pos) if len(pos) else 0.0) * m["point"])
    e9 = R.ema(d["c"], 9)
    up = np.r_[False, e9[1:] > e9[:-1]]
    dn = np.r_[False, e9[1:] < e9[:-1]]
    wk = weekly_up(d)
    s200 = R.sma(d["c"], 200)
    cut = d["t"][int(len(d["t"]) * R.SPLIT)]
    trades = []
    for sig in signals(d, up, dn):
        i, setup, side = sig[0], sig[1], sig[2]
        cong = (wk[i] == 1) if side > 0 else (wk[i] == 0)
        f200 = (d["c"][i] > s200[i]) if side > 0 else (d["c"][i] < s200[i])
        res = {}
        for mode in ("mme9", "alvo2x"):
            r = walk(sym, d, up, dn, sig, mode)
            if r is not None:
                res[mode] = r
        if res:
            trades.append(dict(setup=setup, side=side, oos=bool(d["t"][i] >= cut), cong=bool(cong),
                               s200=bool(f200), **{k: [round(x, 4) for x in v] for k, v in res.items()}))
    return sym, {"excluded": False, "cls": cls, "trades": trades}


def summarize(results):
    def st(rs):
        a = np.array(rs)
        if len(a) < 10:
            return None
        return dict(n=len(a), R=round(float(a.mean()), 3), wr=round(float((a > 0).mean() * 100), 1),
                    t=round(float(a.mean() / a.std(ddof=1) * np.sqrt(len(a))), 2),
                    win=round(float(a[a > 0].mean()), 2) if (a > 0).any() else 0.0,
                    loss=round(float(a[a <= 0].mean()), 2) if (a <= 0).any() else 0.0)
    rows = []
    for cls in ("Acoes", "Indices", "Forex", "Cripto", "Commodities", "TODOS"):
        for setup in SETUPS:
            for side_name, sides in (("compra", (1,)), ("ambos", (1, -1))):
                for filt in ("nenhum", "semanal", "semanal+SMA200"):
                    for mode in ("mme9", "alvo2x"):
                        for per in ("IS", "OOS"):
                            rs, rs_ns = [], []
                            for sym, res in results.items():
                                if not res or res["excluded"] or (cls != "TODOS" and res["cls"] != cls):
                                    continue
                                for t in res["trades"]:
                                    if t["setup"] != setup or t["side"] not in sides or mode not in t:
                                        continue
                                    if (per == "OOS") != t["oos"]:
                                        continue
                                    if filt != "nenhum" and not t["cong"]:
                                        continue
                                    if filt == "semanal+SMA200" and not t["s200"]:
                                        continue
                                    rs.append(t[mode][0])
                                    rs_ns.append(t[mode][1])
                            rows.append(dict(cls=cls, setup=setup, side=side_name, filt=filt, mode=mode, per=per,
                                             swap=st(rs), noswap=st(rs_ns)))
    return rows


def main():
    from multiprocessing import Pool
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    syms = sorted(s for s in R._meta() if os.path.exists(os.path.join(R.DATA, f"{s}_D1.npy")))
    results = {}
    with Pool(procs) as pool:
        for sym, res in pool.imap_unordered(run_symbol, syms):
            results[sym] = res
    rows = summarize(results)
    excl = sum(1 for r in results.values() if r and r["excluded"])
    used = sum(1 for r in results.values() if r and not r["excluded"])
    out = "9x_fiel_spread_normal.json" if os.environ.get("SPREAD_NORMAL") else "9x_fiel.json"
    json.dump(dict(used=used, excluded=excl, rows=rows), open(os.path.join(R.DATA, out), "w"), indent=1)
    print(f"ativos usados: {used} | CFDs de acoes excluidos pelo artefato A6: {excl}")
    for r in rows:
        if r["cls"] == "TODOS" and r["side"] == "compra" and r["per"] == "OOS":
            s, ns = r["swap"], r["noswap"]
            if s:
                print(f"{r['setup']} {r['filt']:<15} {r['mode']:<6} OOS: {s['n']:5d} tr  {s['R']:+.3f} R/trade "
                      f"(sem swap {ns['R']:+.3f})  acerto {s['wr']:.0f}%  t {s['t']:+.2f}  ganho {s['win']} perda {s['loss']}")


if __name__ == "__main__":
    main()
