#!/usr/bin/env python3
"""
query_memory.py — Consulta o RAG da memória permanente (BM25).

Uso:
  python memoria/scripts/query_memory.py "pergunta livre"
  python memoria/scripts/query_memory.py "setup 9.2 correção" -k 5
  python memoria/scripts/query_memory.py "gestão de risco" --kind wiki   # só wiki destilada
  python memoria/scripts/query_memory.py "expectativa matemática" --text # só texto bruto (sem preview truncado)

Sem índice: chama build_memory.py automaticamente.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent  # memoria/
INDEX_FILE = BASE_DIR / "index" / "memoria_index.json"

TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.\d+)?")
STOPWORDS = set("""
a o e é de da do dos das em no na nos nas um uma para por com sem que não nãos ao aos as à às
se como mas mais menos muito pouca pouco sobre até depois antes quando onde qual quais este esta
estes estas esse essa esses essas isso isto já ainda também ser ter haver pode estão estão entre
cada todos todas toda todo vez vezes forma forma assim depois ou não é são foi foram eram seria
""".split())

K1 = 1.5
B = 0.75


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    toks = TOKEN_RE.findall(_norm(text).lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]


def load_index() -> dict:
    if not INDEX_FILE.exists():
        print("[query_memory] índice não encontrado — construindo...")
        subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "build_memory.py")], check=True)
    with open(INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


def bm25_score(index: dict, query_tokens: list[str], k: int = 5) -> list[dict]:
    N = index["N"]
    avgdl = index["avgdl"]
    df = index["df"]
    postings = index["postings"]
    corpus = index["corpus"]

    q_terms = [t for t in set(query_tokens) if t in df]
    if not q_terms:
        return []

    scores: dict[int, float] = Counter()
    for term in q_terms:
        idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
        for doc_idx_raw, tf in postings[term].items():
            doc_idx = int(doc_idx_raw)
            dl = len(tokenize(corpus[doc_idx]["text"]))
            scores[doc_idx] += idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / avgdl))

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return [{"chunk": corpus[idx], "score": round(s, 3)} for idx, s in ranked]


def main() -> int:
    ap = argparse.ArgumentParser(description="Consulta a memória permanente (RAG BM25)")
    ap.add_argument("query", help="Pergunta ou termos de busca")
    ap.add_argument("-k", type=int, default=4, help="Número de resultados (default 4)")
    ap.add_argument("--kind", choices=["raw", "wiki"], help="Filtrar por tipo de fonte")
    ap.add_argument("--text", action="store_true", help="Mostrar bloco inteiro (sem truncar)")
    args = ap.parse_args()

    index = load_index()
    results = bm25_score(index, tokenize(args.query), k=args.k)

    if not results:
        print("[query_memory] nenhum resultado. Tente outros termos ou rebuild.")
        return 1

    shown = 0
    for r in results:
        chunk = r["chunk"]
        if args.kind and chunk["kind"] != args.kind:
            continue
        shown += 1
        text = chunk["text"].strip()
        if not args.text and len(text) > 500:
            text = text[:500] + " ..."
        print(f"\n=== [{r['score']:.2f}] {chunk['path']} (id={chunk['id']}) ===")
        print(text)

    if shown == 0:
        print("[query_memory] filtro --kind não retornou nada.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
