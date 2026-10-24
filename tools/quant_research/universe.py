"""Lista os simbolos da corretora operaveis com conta pequena (so leitura, nenhuma ordem).

Uso: python universe.py [saldo] [max_margem_pct]
Para cada simbolo visivel/negociavel calcula, no lote minimo: margem, valor de 1 ATR(D1)
em USD e custo do spread em USD. Grava data/universe.json com os que cabem no saldo.
"""
import json
import sys

import MetaTrader5 as m
import numpy as np

BAL = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
MAX_MARGIN_PCT = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0

if not m.initialize():
    raise SystemExit(f"MT5 indisponivel: {m.last_error()}")
rows = []
for s in m.symbols_get() or []:
    if s.trade_mode != m.SYMBOL_TRADE_MODE_FULL:
        continue
    m.symbol_select(s.name, True)
    t = m.symbol_info_tick(s.name)
    if t is None or not t.ask or not t.bid:
        continue
    vmin = s.volume_min
    margin = m.order_calc_margin(m.ORDER_TYPE_BUY, s.name, vmin, t.ask)
    step = t.bid * 0.01
    prof = m.order_calc_profit(m.ORDER_TYPE_BUY, s.name, vmin, t.bid, t.bid + step)
    if margin is None or prof is None or prof <= 0:
        continue
    upu = prof / step  # USD por unidade de preco no lote minimo
    d1 = m.copy_rates_from_pos(s.name, m.TIMEFRAME_D1, 1, 30)
    atr_usd = None
    if d1 is not None and len(d1) >= 15:
        tr = d1["high"] - d1["low"]
        atr_usd = float(np.mean(tr[-14:]) * upu)
    rows.append(dict(sym=s.name, path=s.path, vmin=vmin, margin=round(margin, 3),
                     spread_usd=round((t.ask - t.bid) * upu, 4),
                     atr_d1_usd=None if atr_usd is None else round(atr_usd, 3),
                     swapL=s.swap_long, swapS=s.swap_short, swap_mode=s.swap_mode,
                     point=s.point, usd_per_unit=upu, price=t.bid))
ok = [r for r in rows if r["margin"] <= BAL * MAX_MARGIN_PCT / 100 and r["atr_d1_usd"]]
ok.sort(key=lambda r: r["atr_d1_usd"])
json.dump(dict(balance=BAL, all=rows, ok=ok), open("data/universe.json", "w"), indent=1)
print(f"{len(rows)} negociaveis, {len(ok)} com margem <= {MAX_MARGIN_PCT}% de ${BAL}")
for r in ok:
    print(f"{r['sym']:<12} {r['path'].split(chr(92))[0]:<14} margem ${r['margin']:<7} "
          f"spread ${r['spread_usd']:<8} ATR(D1) ${r['atr_d1_usd']}")
