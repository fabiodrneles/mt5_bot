"""Varredura de padroes de calendario/horario (sazonalidade intradiaria e mensal).

So le historico. Uso: python seasonal2.py -> data/s2.json e imprime os sobreviventes.

Cada "celula" e (simbolo, dia da semana ou todos, hora de entrada, horas seguradas, lado).
Para cada ocorrencia: compra/vende na abertura da hora (pagando o maior spread entre o candle
anterior e o de entrada) e sai no fechamento da ultima hora (venda paga o spread do fechamento).
Celulas de data: (simbolo, dia util do mes a partir do inicio ou do fim, lado), no D1.

Controle de falsas descobertas (registrado antes de rodar):
 1. IS = 60% iniciais. p-valor unilateral do t no IS; Benjamini-Hochberg com q = 5% sobre TODAS as celulas.
 2. Sobrevivente do BH precisa, no OOS: mesmo sinal, lucro > 0 depois de custos, t >= 2.
 3. Estabilidade: lucro em >= 70% dos anos com >= 20 ocorrencias.
 4. Custo 1,5x ainda positivo no OOS.
"""
import json
import math
import os
import sys
from statistics import NormalDist

import numpy as np

import research2 as R

N01 = NormalDist()
HOLDS = (1, 2, 4)


def tstat(p):
    if len(p) < 3:
        return 0.0
    sd = p.std(ddof=1)
    return float(p.mean() / sd * math.sqrt(len(p))) if sd > 0 else 0.0


def summarize(sym, kind, wd, h, k, side, p, te, yr, cut, move, cost):
    """Resume a celula na hora (nao guarda os vetores: a maquina-alvo tem 4 GB)."""
    is_ = te < cut
    pis, poos = p[is_], p[~is_]
    yrs = {}
    for y, v in zip(yr.tolist(), p.tolist()):
        yrs.setdefault(y, []).append(v)
    yr_pos = [sum(v) > 0 for v in yrs.values() if len(v) >= 20]
    return dict(sym=sym, kind=kind, wd=wd, h=h, k=k, side=side, n_is=int(len(pis)), t_is=tstat(pis),
                is_net=float(pis.sum()), n_oos=int(len(poos)), t_oos=tstat(poos), oos_net=float(poos.sum()),
                oos_avg=float(poos.mean()) if len(poos) else 0.0,
                stab=sum(yr_pos) / len(yr_pos) if yr_pos else 0.0,
                oos_cost15=float((move[~is_] - 1.5 * cost[~is_]).sum()),
                avg_cost=float(cost.mean()), gross_avg=float(move.mean()), n=int(len(p)))


def intraday_cells(sym):
    d = R.load(sym, "H1")
    m = R._meta()[sym]
    upu, comm = m["usd_per_unit"], m["comm_rt"]
    o, c, t, day = d["o"], d["c"], d["t"], d["day"]
    spr_in = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]])
    spr_out = np.maximum(d["spr"], np.r_[d["spr"][1:], d["spr"][-1:]])
    n = len(c)
    cut = t[int(n * R.SPLIT)]
    hour, dow = d["hour"], d["dow"]
    year = t.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970
    out = []
    for k in HOLDS:
        x = np.arange(n - k + 1) + k - 1  # indice do ultimo candle segurado
        e = np.arange(n - k + 1)
        same_day = day[x] == day[e]
        contiguous = (t[x] - t[e]) == (k - 1) * 3600
        ok = same_day & contiguous
        # 1o candle depois de pausa: abertura irreal no historico -> entra pelo pior entre abertura e
        # fechamento anterior (mesma regra do research2.simulate).
        pause = np.r_[False, np.diff(t) > 5400]
        prev_c = np.r_[c[:1], c[:-1]]
        o_long = np.where(pause[e], np.maximum(o[e], prev_c[e]), o[e])
        o_short = np.where(pause[e], np.minimum(o[e], prev_c[e]), o[e])
        move = c[x] - o_long
        move_s = c[x] - o_short
        long_usd = (move - spr_in[e]) * upu - comm
        short_usd = (-move_s - spr_out[x]) * upu - comm
        for wd in (-1, 0, 1, 2, 3, 4):
            sel_wd = ok & ((dow[e] == wd) if wd >= 0 else True)
            for h in range(1, 24):  # hora 0 = rollover: candles nao precificam o spread real (ver research2)
                sel = sel_wd & (hour[e] == h)
                if sel.sum() < 60:
                    continue
                for side, pnl in ((1, long_usd), (-1, short_usd)):
                    p = pnl[sel]
                    te = t[e][sel]
                    out.append(summarize(sym, "hour", wd, h, k, side, p, te, year[e][sel], cut,
                                         (move[sel] if side > 0 else -move_s[sel]) * upu,
                                         (spr_in[e][sel] if side > 0 else spr_out[x][sel]) * upu + comm))
    return out


def month_cells(sym):
    d = R.load(sym, "D1")
    m = R._meta()[sym]
    upu, comm = m["usd_per_unit"], m["comm_rt"]
    o, c, t, spr = d["o"], d["c"], d["t"], d["spr"]
    mon = d["month"]
    n = len(c)
    cut = t[int(n * R.SPLIT)]
    first = np.r_[True, mon[1:] != mon[:-1]]
    grp = np.cumsum(first)
    pos = np.arange(n) - np.flatnonzero(first)[grp - 1]  # 0 = 1o dia util do mes
    size = np.bincount(grp)[grp]
    from_end = size - 1 - pos  # 0 = ultimo dia util
    year = t.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970
    prev_c = np.r_[c[:1], c[:-1]]
    move_l = c - np.maximum(o, prev_c)  # abertura diaria irreal em CFDs: pior preco (ver research2)
    move_s = c - np.minimum(o, prev_c)
    out = []
    for kind, idx in (("tdm", pos), ("tdm_end", from_end)):
        for v in range(0, 6):
            sel = idx == v
            if sel.sum() < 60:
                continue
            for side in (1, -1):
                mv = move_l[sel] if side > 0 else -move_s[sel]
                p = (mv - spr[sel]) * upu - comm
                out.append(summarize(sym, kind, -1, v, 1, side, p, t[sel], year[sel], cut,
                                     mv * upu, spr[sel] * upu + comm))
    return out


def main():
    meta = R._meta()
    cells = []
    for sym in sorted(meta):
        for fn in (intraday_cells, month_cells):
            try:
                cells += fn(sym)
            except (FileNotFoundError, KeyError, ValueError, OSError):
                pass
    print(f"celulas testadas: {len(cells)}", flush=True)
    pv = [1 - N01.cdf(c["t_is"]) if c["n_is"] >= 30 else 1.0 for c in cells]
    pv = np.array(pv)
    order = np.argsort(pv)
    m_tests = len(pv)
    thr = 0.05 * np.arange(1, m_tests + 1) / m_tests
    passed = pv[order] <= thr
    k_max = np.flatnonzero(passed).max() + 1 if passed.any() else 0
    bh = set(order[:k_max].tolist())
    print(f"sobreviventes do BH (q=5%) no IS: {len(bh)}", flush=True)
    survivors, table = [], []
    for i in bh:
        c = cells[i]
        row = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()}
        row["group"] = meta[c["sym"]].get("group", "")
        row["ok"] = c["oos_net"] > 0 and c["t_oos"] >= 2 and c["stab"] >= 0.7 and c["oos_cost15"] > 0
        table.append(row)
        if row["ok"]:
            survivors.append(row)
    table.sort(key=lambda r: -r["t_oos"])
    json.dump(dict(tested=m_tests, bh=len(bh), survivors=survivors, bh_table=table),
              open(os.path.join(R.DATA, "s2.json"), "w"), indent=1, default=float)
    print(f"aprovados (BH + OOS + estabilidade + custo 1,5x): {len(survivors)}")
    for r in table[:40]:
        print(r)
    # Diagnostico: quantas celulas tem movimento bruto medio a favor maior que o custo medio?
    gross_beats = sum(1 for c in cells if c["gross_avg"] > c["avg_cost"])
    print(f"celulas cujo movimento medio bruto supera o custo medio (sem selecao): {gross_beats} de {len(cells)}")


if __name__ == "__main__":
    sys.exit(main())
