"""Gera RESULTADOS2.md (versionado) a partir de data/a2.json e data/r2_*.jsonl.

Uso: python report2.py
"""
import json
import os
from collections import defaultdict

import numpy as np

import analyze2 as A
import research2 as R

OUT = os.path.join(R.HERE, "RESULTADOS2.md")


def fmt_par(p):
    return ", ".join(f"{k}={v}" for k, v in p.items())


def family_board():
    """Por familia: em quantas celulas (simbolo x TF) o parametro escolhido no IS lucrou no OOS."""
    board = defaultdict(lambda: dict(cells=0, oos_pos=0, both=0, ts=[]))
    for tf in ("D1", "H4", "H1", "M30", "M15"):
        for rec in A.load_rows(tf):
            for c in A.stage_a(rec):
                b = board[c["fam"]]
                b["cells"] += 1
                b["oos_pos"] += c["OOS"]["net"] > 0
                b["both"] += c["OOS"]["net"] > 0 and c["IS"]["net"] > 0
                if c["OOS"]["n"] >= 10:
                    b["ts"].append(c["OOS"]["t"])
    rows = []
    for fam, b in board.items():
        rows.append((fam, b["cells"], b["oos_pos"] / b["cells"] * 100, b["both"] / b["cells"] * 100,
                     float(np.median(b["ts"])) if b["ts"] else 0.0))
    return sorted(rows, key=lambda r: -r[4])


def main():
    a2 = json.load(open(os.path.join(R.DATA, "a2.json")))
    L = ["# Resultados da pesquisa ampla (rodada 3)", "",
         "> Gerado por `report2.py`. Protocolo registrado antes dos resultados: [PROTOCOLO2.md](PROTOCOLO2.md).",
         "> Valores em US$ no **lote mínimo**, com spread, comissão e swap. Passado não garante futuro.", "",
         "## O que foi testado", "", "| TF | Símbolos | Configurações | Desvio do Sharpe/trade entre configurações |",
         "|---|---|---|---|"]
    total = 0
    for tf, t in a2["tested"].items():
        L.append(f"| {tf} | {t['symbols']} | {t['configs']:,} | {t['sr_std']} |".replace(",", "."))
        total += t["configs"]
    L += ["", f"Total: **{total:,} configurações**.".replace(",", "."), "",
          "## Funil dos critérios", "", "| TF | Células (símbolo × família) | 1: OOS forte | 1+2: IS também | 1+2+3: família robusta |",
          "|---|---|---|---|---|"]
    for tf, c in a2["cells"].items():
        L.append(f"| {tf} | {c['total']} | {c['c1']} | {c['c12']} | {c['c123']} |")
    L += ["", f"Passaram 1–3 e foram para os testes 4–7: **{len(a2['candidates']) + len(a2['promising'])}**. "
          f"Aprovadas em todos os 7: **{len(a2['candidates'])}**.", ""]

    def table(rows, title):
        out = [f"## {title}", ""]
        if not rows:
            return out + ["Nenhuma.", ""]
        out += ["| Símbolo | TF | Família | Parâmetros | OOS trades | OOS lucro | OOS PF | t | Custo 1,5× | Walk-forward (5 dobras) | DSR | Risco/trade | Ruína 2 anos | Generaliza | Falhou |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in sorted(rows, key=lambda c: -c["OOS"]["t"]):
            fail = [k for k in ("c4", "c5", "c6", "c7") if not c[k]]
            out.append(f"| {c['sym']} | {c['tf']} | {c['fam']} | {fmt_par(c['par'])} | {c['OOS']['n']} | "
                       f"{c['OOS']['net']:+.2f} | {c['OOS']['pf']} | {c['OOS']['t']} | {c['stress']['1.5']:+.2f} | "
                       f"{' / '.join(f'{x:+.2f}' for x in c['wf'])} | {c['dsr']} | ${c['risk']} | "
                       f"{c['ruin'] * 100:.1f}% | {c['gen']} | {', '.join(fail) or '—'} |")
        return out + [""]

    L += table(a2["candidates"], "Aprovadas nos 7 critérios")
    L += table(a2["promising"], "Promissoras (passaram 1–3, falharam em algum de 4–7)")
    L += ["Legenda das falhas: c4 = não sobrevive a custo 1,5×; c5 = *walk-forward* fraco; c6 = Deflated Sharpe < 0,95 "
          "(pode ser sorte, dado o número de testes); c7 = não cabe na conta de $16.", "",
          "## Placar por família (todas as células)", "",
          "| Família | Células | OOS > 0 | IS e OOS > 0 | t mediano no OOS |", "|---|---|---|---|---|"]
    for fam, n, pos, both, t in family_board():
        L.append(f"| {fam} | {n} | {pos:.0f}% | {both:.0f}% | {t:+.2f} |")
    L += ["", "Uma família sem vantagem teria cerca de 50% de OOS positivo antes dos custos e menos depois deles.", ""]
    pairs_path = os.path.join(R.DATA, "r2_pairs.json")
    if os.path.exists(pairs_path):
        L += ["## Pares (D1)", "", "| Par | L | z | Lotes | IS lucro | OOS trades | OOS lucro | OOS t | Margem |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(json.load(open(pairs_path)), key=lambda r: -r["OOS"]["t"]):
            L.append(f"| {r['pair']} | {r['L']} | {r['z']} | {r['lots'][0]}:{r['lots'][1]} | {r['IS']['net']:+.2f} | "
                     f"{r['OOS']['n']} | {r['OOS']['net']:+.2f} | {r['OOS']['t']} | ${r['margin']} |")
        L.append("")
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print("ok", OUT)


if __name__ == "__main__":
    main()
