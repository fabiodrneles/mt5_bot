"""Regra do dono, versao 5 (2026-10-24): forca da tendencia pela INCLINACAO, lida como um relogio.
Entre 12h e 2h (ou 4h e 6h na queda) = tendencia forte; perto das 3h = fraca. O sinal da MME9 so vale como
reversao depois de tendencia forte.

So le historico. Uso: python check_clock.py SYM TF
O angulo visto no grafico depende do zoom. Para o robo, a inclinacao e medida em ATR por candle:
  s = (MM[i-1] - MM[i-1-N]) / (N * ATR[i-1])
e lida no relogio supondo 1 ATR/candle = 45 graus (1h30). Como o zoom muda essa escala, os cortes de "forte"
sao testados por quantil (|s| entre os 50/30/20/10% mais inclinados), o que vale para qualquer zoom.
Cada sinal: stop na maxima/minima do candle, alvo 2x (e 1x), custos reais. IS = 60% iniciais; OOS = 40% finais.
"""
import datetime as dt
import itertools
import math
import sys

import numpy as np

import check_ema9_filters as C
import check_exits as X
import research2 as R
import signal_mining as S


def clock(s):
    """Inclinacao (ATR/candle) -> hora no relogio (3h = deitada, 12h = vertical para cima, 6h = para baixo)."""
    ang = math.degrees(math.atan(s))
    return 3 - ang / 30


def slope(d, line, N):
    A = R.atr(d, 14)
    mm = R.ema(d["c"], line)
    return R.lag((mm - R.lag(mm, N)) / (N * A))


def st(p):
    p = p[np.isfinite(p)]
    if len(p) < 3 or p.std() == 0:
        return f"{len(p):4d} tr"
    return f"{len(p):4d} tr acerto {np.mean(p > 0) * 100:5.1f}% ${p.sum():+7.2f} t {p.mean() / p.std(ddof=1) * np.sqrt(len(p)):+5.2f}"


def main():
    sym, tf = sys.argv[1], sys.argv[2]
    d = R.load(sym, tf)
    f = C.features(d)
    _, sig, dist = C.run_rule(sym, d, f, 0.0, "nenhum", "ambos")
    res2 = S.outcomes(sym, d, sig, dist)
    exits, _ = X.simulate_exits(sym, d, sig, dist)
    res1 = exits["alvo 1.0x"]
    has = np.isfinite(res2)
    idx = np.flatnonzero(has)
    cut = d["t"][idx[int(len(idx) * R.SPLIT)]]
    is_m, oos_m = has & (d["t"] < cut), has & (d["t"] >= cut)
    print(f"{sym} {tf}: todos os sinais (alvo 2x)  IS {st(res2[is_m])} | OOS {st(res2[oos_m])}")

    if sym == "US500":
        print("Exemplos do dono, inclinacao antes do sinal (MME9, 10 candles) lida no relogio (1 ATR/candle = 1h30):")
        for when, tfx, lab in (("2026-10-16 16:30", "M15", "bom"), ("2026-10-19 09:00", "M15", "ruim"),
                               ("2026-10-16 16:30", "M30", "bom"), ("2026-10-19 01:00", "M30", "bom")):
            if tfx != tf:
                continue
            ts = int(dt.datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).timestamp())
            i = int(np.flatnonzero(d["t"] == ts)[0])
            s9 = slope(d, 9, 10)[i]
            print(f"   {when} ({lab}): {s9:+.2f} ATR/candle -> {clock(s9):.1f}h  | resultado {res2[i]:+.2f}")

    rows = []
    for line, N, q in itertools.product((9, 21), (5, 10, 20), (50, 70, 80, 90)):
        s = slope(d, line, N)
        thr = np.nanpercentile(np.abs(s[idx[: int(len(idx) * R.SPLIT)]]), q)  # corte calibrado so no IS
        keep = ((sig > 0) & (s <= -thr)) | ((sig < 0) & (s >= thr))      # reversao depois de tendencia inclinada
        rows.append(((line, N, q, thr), keep))
    print(f"\n{len(rows)} definicoes de 'tendencia inclinada' (MME 9/21; N 5/10/20; os 50/30/20/10% mais inclinados)")
    for name, res in (("alvo 2x", res2), ("alvo 1x", res1)):
        scored = []
        for par, keep in rows:
            p = res[keep & is_m]
            p = p[np.isfinite(p)]
            if len(p) >= 30 and p.std() > 0:
                scored.append((p.mean() / p.std(ddof=1) * np.sqrt(len(p)), par, keep))
        scored.sort(key=lambda r: -r[0])
        both = sum(1 for _, _, k in scored if np.nansum(res[k & is_m]) > 0 and np.nansum(res[k & oos_m]) > 0)
        print(f"\n{name}: {both} de {len(scored)} definicoes lucram no IS e no OOS. Melhores no IS:")
        for _, (line, N, q, thr), keep in scored[:5]:
            print(f"   MME{line:<2} N{N:<2} top {100 - q}% (|s| >= {thr:.2f} ~ antes de {clock(thr):.1f}h)  "
                  f"IS {st(res[keep & is_m])} | OOS {st(res[keep & oos_m])}")


if __name__ == "__main__":
    main()
