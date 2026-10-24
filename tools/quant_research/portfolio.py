"""Mesmo PULLB (k=1, R=2, sem otimizar) em todos os ativos baratos: o efeito e geral?"""
import sys, numpy as np, collections
from datetime import datetime, timezone
import research as R

def pullb_trades(sym, tf, k=1.0, Rm=2.0, intra=False, sprmult=1.0):
    d = R.load(sym, tf); d["spr"] = d["spr"] * sprmult
    for nm, p, sig, stop, tgt, xl, xs, mb, it in R.strategies(d):
        if nm == "PULLB" and p == {'k': k, 'R': Rm, 'intra': intra}:
            return R.simulate(sym, d, sig, stop, tgt, xl, xs, mb, it), d
    raise SystemExit("config nao encontrada")

def years(tr):
    y = collections.defaultdict(float)
    for t, dr, u, b in tr: y[datetime.fromtimestamp(int(t), timezone.utc).year] += u
    return y

if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "H4"
    syms = "HK50,JP225,US500,FR40,AU200,EU50,UK100,CN50,USOIL+,UKOIL+".split(",")
    print(f"PULLB {tf} k=1 R=2 (fixo) | metade1 = 1a metade dos trades, metade2 = 2a")
    for s in syms:
        tr, d = pullb_trades(s, tf)
        st = R.stats(tr); h = len(tr) // 2
        a, b = R.stats(tr[:h]), R.stats(tr[h:])
        A = R.atr(d, 14)[-500:] * R.META[s]["usd_per_unit"]
        y = years(tr); pos = sum(v > 0 for v in y.values())
        st15 = R.stats(pullb_trades(s, tf, sprmult=1.5)[0])
        print(f"{s:7} n{st['n']:4} pf{st['pf']:5} net${st['net']:7.2f} dd${st['dd']:6.2f} | h1 ${a['net']:6.2f} h2 ${b['net']:6.2f} | anos+ {pos}/{len(y)} | spr1.5 ${st15['net']:6.2f} | risco med ${np.median(A):.2f}")
