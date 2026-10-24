"""Lead-lag entre ativos: o movimento de A na ultima hora preve o de B na hora seguinte?

So le historico. Uso: python leadlag2.py -> data/ll2.json
Universo: forex, indices, commodities e cripto de data/meta2.json com H1 (sem acoes: horario curto).
Regras testadas para cada par ordenado (A -> B), alinhadas pelo horario do candle:
  - "sign": opera B na direcao (ou contra) do retorno de A no candle anterior;
  - "big":  so quando |retorno de A| > z desvios (z = 1, 2), na direcao ou contra.
Entrada em B na abertura do candle seguinte (pagando o maior spread entre o anterior e o de entrada),
saida no fechamento do mesmo candle. Mesmos controles do seasonal2: BH q=5% no IS, OOS t>=2 e
lucro > 0, estabilidade anual >= 70%, custo 1,5x positivo.
"""
import itertools
import json
import os

import numpy as np

import research2 as R
import seasonal2 as S


def load_returns(sym):
    d = R.load(sym, "H1")
    m = R._meta()[sym]
    spr_in = np.maximum(d["spr"], np.r_[d["spr"][:1], d["spr"][:-1]])
    spr_out = np.maximum(d["spr"], np.r_[d["spr"][1:], d["spr"][-1:]])
    move = (d["c"] - d["o"]) * m["usd_per_unit"]
    ret = np.log(d["c"] / d["o"])
    return dict(t=d["t"], ret=ret, move=move, cin=spr_in * m["usd_per_unit"] + m["comm_rt"],
                cout=spr_out * m["usd_per_unit"] + m["comm_rt"])


def main():
    meta = R._meta()
    syms = [s for s in sorted(meta) if not meta[s].get("group", "").startswith("CFD Stocks")
            and os.path.exists(os.path.join(R.DATA, f"{s}_H1.npy"))]
    data = {}
    for s in syms:
        try:
            data[s] = load_returns(s)
        except (ValueError, OSError, KeyError):
            pass
    syms = list(data)
    print("ativos:", len(syms), flush=True)
    cells = []
    for a, b in itertools.permutations(syms, 2):
        A, B = data[a], data[b]
        # sinal de A no candle que fecha em t; B opera o candle que abre em t + 1h
        want = B["t"] - 3600
        pos = np.clip(np.searchsorted(A["t"], want), 0, len(A["t"]) - 1)
        jb = np.where(A["t"][pos] == want, pos, -1)
        ok = jb >= 0
        if ok.sum() < 2000:
            continue
        bi = np.flatnonzero(ok)
        ra = A["ret"][jb[ok]]
        sd = np.std(ra)
        cut = B["t"][bi[int(len(bi) * R.SPLIT)]]
        te = B["t"][bi]
        yr = te.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970
        mv, cin, cout = B["move"][bi], B["cin"][bi], B["cout"][bi]
        for rule, z in (("sign", 0.0), ("big", 1.0), ("big", 2.0)):
            sel = np.abs(ra) > z * sd if z > 0 else ra != 0
            if sel.sum() < 100:
                continue
            for follow in (1, -1):
                side = np.sign(ra[sel]) * follow
                gross = side * mv[sel]
                cost = np.where(side > 0, cin[sel], cout[sel])
                p = gross - cost
                c = S.summarize(f"{a}->{b}", rule, -1, z, 1, follow, p, te[sel], yr[sel], cut, gross, cost)
                cells.append(c)
    print("celulas:", len(cells), flush=True)
    pv = np.array([1 - S.N01.cdf(c["t_is"]) if c["n_is"] >= 30 else 1.0 for c in cells])
    order = np.argsort(pv)
    thr = 0.05 * np.arange(1, len(pv) + 1) / len(pv)
    passed = pv[order] <= thr
    k_max = np.flatnonzero(passed).max() + 1 if passed.any() else 0
    bh = order[:k_max]
    table = []
    for i in bh:
        c = dict(cells[i])
        c["ok"] = c["oos_net"] > 0 and c["t_oos"] >= 2 and c["stab"] >= 0.7 and c["oos_cost15"] > 0
        table.append(c)
    table.sort(key=lambda r: -r["t_oos"])
    gross_pos = sum(1 for c in cells if c["gross_avg"] > 0)
    beats = sum(1 for c in cells if c["gross_avg"] > c["avg_cost"])
    json.dump(dict(tested=len(cells), bh=len(bh), survivors=[c for c in table if c["ok"]], bh_table=table,
                   gross_pos=gross_pos, beats_cost=beats), open(os.path.join(R.DATA, "ll2.json"), "w"),
              indent=1, default=float)
    print(f"BH: {len(bh)}  aprovados: {sum(c['ok'] for c in table)}  "
          f"movimento bruto a favor: {gross_pos}/{len(cells)}  supera o custo: {beats}/{len(cells)}")
    for c in table[:25]:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()})


if __name__ == "__main__":
    main()
