"""Baixa H1 e D1 de todos os simbolos de data/universe.json (so leitura, nenhuma ordem).

Uso: python fetch2.py            (pula arquivos que ja existem)
Grava data/<SYM>_H1.npy e data/<SYM>_D1.npy e data/meta2.json (custos e valor do ponto).
"""
import json
import os
import time

import MetaTrader5 as m

TFS = {"H1": (m.TIMEFRAME_H1, 30000), "D1": (m.TIMEFRAME_D1, 4000)}


def commission_per_lot():
    """Comissao media por lote (so entrada) observada nos deals reais, por simbolo."""
    out = {}
    deals = m.history_deals_get(0, int(time.time()) + 86400) or []
    for d in deals:
        if d.volume > 0 and d.entry == 0 and d.commission:
            out.setdefault(d.symbol, []).append(abs(d.commission) / d.volume)
    return {s: sum(v) / len(v) for s, v in out.items()}


def main():
    import numpy as np
    if not m.initialize():
        raise SystemExit(m.last_error())
    uni = json.load(open("data/universe.json"))["ok"]
    comm = commission_per_lot()
    print("comissao observada:", {k: round(v, 2) for k, v in comm.items()}, flush=True)
    # Prioridade: forex, indices, commodities e cripto antes das acoes (que o servidor entrega devagar).
    uni.sort(key=lambda r: (r["path"].startswith("CFD Stocks"), r["sym"]))
    meta = {}
    for r in uni:
        s = r["sym"]
        m.symbol_select(s, True)
        info = m.symbol_info(s)
        group = r["path"].split("\\")[0]
        # Sem deal real: indices/cripto pagam ~$1/lote na entrada (observado); acoes assumem
        # o mesmo por cautela; FX e petroleo sem comissao (spread embutido).
        default = 0.0 if group.startswith(("FX", "EURUSD", "USOIL", "UKOIL", "Metals")) else 1.0
        meta[s] = dict(point=r["point"], vmin=r["vmin"], price=r["price"], usd_per_unit=r["usd_per_unit"],
                       margin=r["margin"], swapL=r["swapL"], swapS=r["swapS"], swap_mode=r["swap_mode"],
                       swap3=getattr(info, "swap_rollover3days", 3), group=group,
                       comm_rt=comm.get(s, default) * r["vmin"])
    # Metadados gravados antes do download: a pesquisa pode rodar sobre o que ja baixou.
    json.dump(meta, open("data/meta2.json", "w"), indent=1)
    for r in uni:
        s = r["sym"]
        for name, (tf, cnt) in TFS.items():
            f = f"data/{s}_{name}.npy"
            if os.path.exists(f):
                continue
            rates, c = None, cnt
            while c >= 500:
                rates = m.copy_rates_from_pos(s, tf, 1, c)
                if rates is not None and len(rates):
                    break
                c //= 2
            if rates is None or not len(rates):
                print(s, name, "sem dados", m.last_error(), flush=True)
                continue
            np.save(f, rates)
            print(s, name, len(rates), flush=True)
    json.dump(meta, open("data/meta2.json", "w"), indent=1)
    print("ok", len(meta))


if __name__ == "__main__":
    main()
