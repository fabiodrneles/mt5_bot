"""Teste de sorte: t-stat, entradas aleatorias com o mesmo SL/TP e generalizacao do RSI2."""
import numpy as np, research as R
from portfolio import pullb_trades

def tstat(tr):
    p = np.array([x[2] for x in tr]); return p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))

# 1) t-stat
tr, d = pullb_trades("HK50", "H4")
print(f"HK50 H4 PULLB: n={len(tr)} media=${np.mean([x[2] for x in tr]):.4f} t={tstat(tr):.2f}")

# 2) entradas aleatorias: mesmas barras-candidatas de tendencia (sem o toque na EMA20), direcao da tendencia
c = d["c"]; A = R.atr(d, 14); e20 = R.ema(c, 20); e50 = R.ema(c, 50); s200 = R.sma(c, 200)
up = (e20 > e50) & (c > s200); dn = (e20 < e50) & (c < s200)
rng = np.random.default_rng(7); nets = []
nan = np.full(len(c), np.nan)
for it in range(300):
    sig = np.zeros(len(c), int)
    cand = np.flatnonzero(up | dn)
    pick = rng.choice(cand, size=min(len(cand), 700), replace=False)
    sig[pick] = np.where(up[pick], 1, -1)
    rt = R.simulate("HK50", d, sig, 1.0 * A, 2.0 * A, None, None, 200, False)
    nets.append(sum(x[2] for x in rt))
nets = np.array(nets); real = sum(x[2] for x in tr)
print(f"aleatorio a favor da tendencia (mesmo SL/TP): mediana ${np.median(nets):.2f} p95 ${np.percentile(nets,95):.2f} | PULLB ${real:.2f} | percentil {100*(nets<real).mean():.0f}")

# 3) RSI2 D1 (L=5, k=2) com parametros fixos em todos os indices
print("RSI2 D1 L=5 k=2 fixo:")
for s in "US500,HK50,JP225,FR40,AU200,EU50,UK100,CN50".split(","):
    d = R.load(s, "D1")
    for nm, p, sig, stop, tgt, xl, xs, mb, it in R.strategies(d):
        if nm == "RSI2" and p == {'L': 5, 'k': 2.0, 'longonly': False, 'intra': False}:
            t2 = R.simulate(s, d, sig, stop, tgt, xl, xs, mb, it); st = R.stats(t2)
            print(f"  {s:6} n{st['n']:3} pf{st['pf']:5} net${st['net']:7.2f} dd${st['dd']:5.2f} worst${st['worst']:6.2f} t={tstat(t2) if len(t2)>2 else 0:.2f}")
