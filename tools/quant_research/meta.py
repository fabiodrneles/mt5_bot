"""Gera data/meta.json: valor do ponto no lote minimo, swap, margem e comissao."""
import json
import MetaTrader5 as m

m.initialize()
SYMS = "JP225,US500,FR40,AU200,HK50,USOIL+,UKOIL+,ETHUSD,EU50,UK100,CN50,SOLUSD,XRPUSD,LTCUSD,BTCUSD".split(",")
# Comissao observada nos deals reais da conta (USD por lote, so na entrada).
COMM_PER_LOT = {"US500": 1, "AU200": 1, "FR40": 1, "EU50": 1, "UK100": 1, "CN50": 1, "BTCUSD": 1,
                "ETHUSD": 1, "SOLUSD": 1, "XRPUSD": 1, "LTCUSD": 1}
meta = {}
for s in SYMS:
    i = m.symbol_info(s); t = m.symbol_info_tick(s); p = t.bid; step = p * 0.1
    meta[s] = dict(point=i.point, vmin=i.volume_min, price=p,
                   usd_per_unit=m.order_calc_profit(m.ORDER_TYPE_BUY, s, i.volume_min, p, p + step) / step,
                   margin=m.order_calc_margin(m.ORDER_TYPE_BUY, s, i.volume_min, t.ask),
                   swapL=i.swap_long, swapS=i.swap_short, swap_mode=i.swap_mode,
                   comm_rt=COMM_PER_LOT.get(s, 0) * i.volume_min)
json.dump(meta, open("data/meta.json", "w"), indent=1)
print("ok", len(meta))
