"""Minerar filtros para o sinal da MME9 (pedido do dono, 2026-10-24): "um robo que enxergue o que eu vejo".

So le historico. Uso: python signal_mining.py SYM TF AAAA-MM-DD
Cada sinal de cruzamento da MME9 e avaliado SOZINHO (stop na maxima/minima do candle, alvo 2x, custos reais).
Para cada sinal calcula indicadores conhecidos no fechamento do candle (nada do futuro).

Parte A: acha regras (1 ou 2 condicoes de limiar) que, no dia pedido, selecionam so os vencedores,
         e mostra o que cada regra faz em TODOS os outros dias do historico.
Parte B: o mesmo tipo de busca, mas escolhendo a regra nos 60% iniciais dos sinais (IS) e medindo nos
         40% finais (OOS) -- e o que um robo poderia fazer de fato.
"""
import datetime as dt
import itertools
import sys

import numpy as np

import check_ema9_filters as C
import research2 as R

RR = 2.0


def outcomes(sym, d, sig, dist):
    """Resultado em US$ de cada sinal sozinho (mesmas regras de custo do research2.simulate)."""
    m = R._meta()[sym]
    o, h, l, c, t = d["o"], d["h"], d["l"], d["c"], d["t"]
    spr = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]])
    upu, comm = m["usd_per_unit"], m["comm_rt"]
    bar = np.median(np.diff(t))
    pause = np.r_[False, np.diff(t) > bar * 1.5]
    res = np.full(len(c), np.nan)
    for i in np.flatnonzero(sig):
        e = i + 1
        if e >= len(c) or (d.get("tf") != "D1" and d["hour"][e] == 0):
            continue
        dr = sig[i]
        entry = o[e] if not pause[e] else (max(o[e], c[i]) if dr > 0 else min(o[e], c[i]))
        sd = dist[i]
        sl, tp = entry - dr * sd, entry + dr * RR * sd
        for j in range(e, len(c)):
            if dr > 0:
                if l[j] <= sl:
                    px = min(o[j], sl) if j > e else sl
                    break
                if h[j] >= tp:
                    px = tp
                    break
            else:
                if h[j] + spr[j] >= sl:
                    px = max(o[j], sl - spr[j]) if j > e else sl - spr[j]
                    break
                if l[j] + spr[j] <= tp:
                    px = tp - spr[j]
                    break
        else:
            continue
        res[i] = (dr * (px - entry) - spr[e]) * upu - comm
    return res


def session_vwap(d):
    h, l, c, v, day = d["h"], d["l"], d["c"], d["v"], d["day"]
    tp = (h + l + c) / 3
    newd = np.r_[True, day[1:] != day[:-1]]
    grp = np.cumsum(newd)
    start = np.flatnonzero(newd)
    cpv, cv = np.cumsum(tp * v), np.cumsum(v)
    base_pv, base_v = np.r_[0, cpv][start][grp - 1], np.r_[0, cv][start][grp - 1]
    return (cpv - base_pv) / np.maximum(cv - base_v, 1)


def feature_table(d, f, sig):
    """Indicadores no fechamento do candle do sinal, orientados pelo lado (positivo = a favor do trade)."""
    c, o, h, l = d["c"], d["o"], d["h"], d["l"]
    A = R.atr(d, 14)
    side = np.where(sig != 0, sig, 1)
    vw = session_vwap(d)
    rsi = R.rsi(c, 14)
    mins = (d["t"] % 86400) // 60 + 15  # minuto do fechamento do candle (horario do servidor)
    feats = {
        "volume/media": f["vrel"],
        "VWAP a favor (ATR)": side * (vw - c) / A * -1,  # >0: venda abaixo do VWAP / compra acima
        "ADX": f["adx"],
        "DI a favor": side * (f["pdi"] - f["ndi"]),
        "IFR14 a favor": side * (rsi - 50),
        "candle/ATR": (h - l) / A,
        "corpo/candle": np.abs(c - o) / np.maximum(h - l, 1e-9),
        "dist MME9 (ATR)": side * (c - f["e9"]) / A,
        "tempos maiores a favor": sum(np.where(side > 0, f["up_" + k] == 1, f["up_" + k] == 0).astype(int)
                                      for k in ("M30", "H1", "H4")),
        "hora": (mins // 60) % 24 + 0.0,
        "min desde abertura EUA": (mins - (16 * 60 + 30)) % 1440 + 0.0,
        "min desde abertura Europa": (mins - 10 * 60) % 1440 + 0.0,
    }
    return feats


def rules(feats, idx):
    """Todas as regras de 1 e 2 condicoes 'feature >= q' ou 'feature <= q' (q nos quantis 10..90%)."""
    conds = []
    for name, x in feats.items():
        vals = x[idx]
        vals = vals[np.isfinite(vals)]
        for q in np.unique(np.percentile(vals, np.arange(10, 91, 10))):
            conds.append((f"{name} >= {q:.2f}", x >= q))
            conds.append((f"{name} <= {q:.2f}", x <= q))
    yield from ((c[0], c[1]) for c in conds)
    for a, b in itertools.combinations(conds, 2):
        if a[0].split(" ")[0] != b[0].split(" ")[0]:
            yield (a[0] + "  E  " + b[0], a[1] & b[1])


def summary(p):
    p = p[np.isfinite(p)]
    if len(p) == 0:
        return "0 trades"
    t = p.mean() / p.std(ddof=1) * np.sqrt(len(p)) if len(p) > 2 and p.std() > 0 else 0.0
    return f"{len(p)} trades, acerto {np.mean(p > 0) * 100:.1f}%, lucro ${p.sum():+.2f}, t {t:+.2f}"


def main():
    sym, tf, day = sys.argv[1], sys.argv[2], sys.argv[3]
    d = R.load(sym, tf)
    f = C.features(d)
    _, sig, dist = C.run_rule(sym, d, f, 0.0, "nenhum", "ambos")
    res = outcomes(sym, d, sig, dist)
    feats = feature_table(d, f, sig)
    has = np.isfinite(res)
    d0 = int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp()) // 86400
    today = has & (d["day"] == d0)
    other = has & (d["day"] != d0)
    win_today = today & (res > 0)
    print(f"Todos os sinais do historico, cada um sozinho: {summary(res[has])}")
    print(f"Dia {day}: {int(today.sum())} sinais, {int(win_today.sum())} vencedores:")
    for i in np.flatnonzero(today):
        hh = dt.datetime.fromtimestamp(int(d["t"][i]), dt.timezone.utc).strftime("%H:%M")
        print(f"   {hh} {'VENDA ' if sig[i] < 0 else 'COMPRA'} ${res[i]:+.2f}  "
              + "  ".join(f"{k.split(' ')[0]}={feats[k][i]:.2f}" for k in list(feats)[:6]))

    # Parte A: regras que separam perfeitamente os vencedores do dia
    n_rules, perfect = 0, []
    for name, mask in rules(feats, np.flatnonzero(has)):
        n_rules += 1
        if (mask & win_today).sum() == win_today.sum() and (mask & today & ~win_today).sum() == 0:
            perfect.append((name, mask))
    print(f"\nPARTE A: {n_rules:,} regras testadas; {len(perfect):,} selecionam EXATAMENTE os vencedores de {day}.".replace(",", "."))
    if perfect:
        outs = [(name, res[mask & other]) for name, mask in perfect]
        outs = [o for o in outs if np.isfinite(o[1]).sum() >= 30]
        tot = np.array([np.nansum(p) for _, p in outs])
        print(f"Nos OUTROS dias do historico, essas regras perfeitas: {np.mean(tot > 0) * 100:.0f}% lucram; "
              f"mediana ${np.median(tot):+.2f}; melhor ${tot.max():+.2f}; pior ${tot.min():+.2f}")
        for name, p in sorted(outs, key=lambda o: -np.nansum(o[1]))[:5]:
            print(f"   melhor: [{name}] -> {summary(p)}")
        for name, p in sorted(outs, key=lambda o: np.nansum(o[1]))[:3]:
            print(f"   pior:   [{name}] -> {summary(p)}")

    # Parte B: regra escolhida no IS, medida no OOS
    idx = np.flatnonzero(has)
    cut = d["t"][idx[int(len(idx) * R.SPLIT)]]
    is_m, oos_m = has & (d["t"] < cut), has & (d["t"] >= cut)
    best = None
    for name, mask in rules(feats, idx):
        p = res[mask & is_m]
        if len(p) >= 50 and p.std() > 0:
            t = p.mean() / p.std(ddof=1) * np.sqrt(len(p))
            if best is None or t > best[0]:
                best = (t, name, mask)
    print(f"\nPARTE B (robo): regra escolhida nos 60% iniciais entre {n_rules:,} -> [{best[1]}]".replace(",", "."))
    print(f"   IS : {summary(res[best[2] & is_m])}")
    print(f"   OOS: {summary(res[best[2] & oos_m])}")


if __name__ == "__main__":
    main()
