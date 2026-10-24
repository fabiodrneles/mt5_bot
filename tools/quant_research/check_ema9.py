"""Regra do dono (2026-10-24): candle que fecha cruzando a MME9 -> entra a favor; risco = tamanho do candle
do sinal; alvo = 2x o risco. So le historico.

Uso: python check_ema9.py SYM TF [AAAA-MM-DD]
Mostra os sinais do dia pedido e o resultado da regra em todo o historico, com custos reais
(simulador research2: spread, comissao, swap, regras de abertura/rollover).
"""
import datetime as dt
import sys

import numpy as np

import research2 as R


def signals(d):
    c, o, h, l = d["c"], d["o"], d["h"], d["l"]
    e9 = R.ema(c, 9)
    prev_above = R.lag((c > e9).astype(float)) == 1
    prev_below = R.lag((c < e9).astype(float)) == 1
    sell = (c < o) & (c < e9) & prev_above      # candle de baixa fecha abaixo da MME9, vinha acima
    buy = (c > o) & (c > e9) & prev_below
    sig = np.zeros(len(c), int)
    sig[buy] = 1
    sig[sell] = -1
    risk = h - l                                  # risco = tamanho do candle do sinal
    return sig, risk, e9


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    day = sys.argv[3] if len(sys.argv) > 3 else None
    d = R.load(sym, tf)
    sig, risk, e9 = signals(d)
    when = lambda i: dt.datetime.fromtimestamp(int(d["t"][i]), dt.timezone.utc).strftime("%d/%m %H:%M")  # noqa: E731
    if day:
        d0 = int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp()) // 86400
        print(f"Sinais em {day} (horario do servidor):")
        for i in np.flatnonzero((d["day"] == d0) & (sig != 0)):
            one = np.zeros_like(sig)
            one[i] = sig[i]
            tr = R.simulate(sym, d, one, risk, 2 * risk, None, None, 10 ** 6, False)
            res = f"resultado ${tr[0, 2]:+.2f} em {int(tr[0, 3])} candles" if len(tr) else "sem entrada"
            print(f"  {when(i)} {'VENDA' if sig[i] < 0 else 'COMPRA'} fecha {d['c'][i]:.2f} MME9 {e9[i]:.2f} "
                  f"risco {risk[i]:.2f} pts -> {res}")
    for side_name, mask in (("ambos", None), ("so venda", -1), ("so compra", 1)):
        s = sig.copy() if mask is None else np.where(sig == mask, sig, 0)
        tr = R.simulate(sym, d, s, risk, 2 * risk, None, None, 10 ** 6, False)
        st = R.stats(tr)
        gross = R.simulate(sym, dict(d, spr=np.zeros_like(d["spr"])), s, risk, 2 * risk, None, None, 10 ** 6, False)
        print(f"{sym} {tf} {side_name}: {st['n']} trades, acerto {st['wr']}%, resultado ${st['net']:+.2f} "
              f"(sem spread ${gross[:, 2].sum():+.2f}), fator de lucro {st['pf']}, t {st['t']}, "
              f"pior queda ${st['dd']}, risco medio ${st['risk']}")
        if mask is None and len(tr):
            yrs = tr[:, 0].astype("datetime64[s]").astype("datetime64[M]")
            for mth in np.unique(yrs)[-12:]:
                p = tr[yrs == mth, 2]
                print(f"    {mth}: {len(p)} trades ${p.sum():+.2f}")


if __name__ == "__main__":
    main()
