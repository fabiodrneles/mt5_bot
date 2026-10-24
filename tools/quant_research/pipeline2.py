"""Roda a pesquisa ampla inteira em sequencia; pode ser interrompido e retomado a qualquer momento.

Uso (com o MT5 aberto, nesta pasta):  python pipeline2.py
Cada etapa pula o que ja fez (arquivos em data/). O log vai para data/pipeline2.log.
"""
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "pipeline2.log")

STEPS = [
    ("universo", [sys.executable, "universe.py", "16", "25"], lambda: os.path.exists(os.path.join(HERE, "data", "universe.json"))),
    ("download H1/D1", [sys.executable, "fetch2.py"], None),
    ("download M15", [sys.executable, "fetch2.py", "--m15"], None),
    ("custos", [sys.executable, "fetch2.py", "--meta-only"], None),
    ("grade 28 familias", [sys.executable, "research2.py", "run", "3"], None),
    ("pares", [sys.executable, "pairs2.py"], None),
    ("criterios 1-7", [sys.executable, "analyze2.py"], None),
    ("sazonalidade", [sys.executable, "seasonal2.py"], None),
    ("lead-lag", [sys.executable, "leadlag2.py"], None),
    ("relatorio", [sys.executable, "report2.py"], None),
]


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    for name, cmd, done in STEPS:
        if done and done():
            log(f"pula: {name} (ja feito)")
            continue
        log(f"inicio: {name}")
        with open(os.path.join(HERE, "data", f"step_{name.split()[0]}.log"), "a", encoding="utf-8") as out:
            rc = subprocess.call(cmd, cwd=HERE, stdout=out, stderr=subprocess.STDOUT)
        log(f"fim: {name} (codigo {rc})")
        if rc != 0:
            log("parou por erro; corrija e rode de novo (as etapas feitas sao puladas)")
            return rc
    log("pipeline completo: veja RESULTADOS2.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
