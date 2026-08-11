#!/usr/bin/env python3
"""
build_memory.py — Constrói o índice BM25 da memória permanente.

Fonte: raw/ (imutável) + wiki/ (conhecimento destilado) -> índice JSON.
Uso: python memoria/scripts/build_memory.py

Saída: memoria/index/ (memoria_index.json + meta)
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # memoria/
RAW_DIR = BASE_DIR / "raw"
WIKI_DIR = BASE_DIR / "wiki"
INDEX_DIR = BASE_DIR / "index"
INDEX_FILE = INDEX_DIR / "memoria_index.json"
META_FILE = INDEX_DIR / "meta.json"

TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.\d+)?")
STOPWORDS = set("""
a o e é de da do dos das em no na nos nas um uma para por com sem que não nãos ao aos as à às
se como mas mais menos muito pouca pouco sobre até depois antes quando onde qual quais este esta
estes estas esse essa esses essas isso isto já ainda também ser ter haver pode estão estão entre
cada todos todas toda todo vez vezes forma forma assim depois ou não é são foi foram eram seria
""".split())


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    toks = TOKEN_RE.findall(_norm(text).lower())
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]


def read_sources() -> list[dict]:
    """Lê todos os .md/.txt de raw/ e wiki/. Retorna [{path, title, text, kind}]."""
    sources = []
    for root_dir in (RAW_DIR, WIKI_DIR):
        for p in sorted(root_dir.rglob("*")):
            if p.is_file() and p.suffix in (".md", ".txt"):
                text = p.read_text(encoding="utf-8", errors="replace")
                rel = p.relative_to(BASE_DIR).as_posix()
                sources.append({
                    "path": rel,
                    "title": p.stem,
                    "text": text,
                    "kind": "raw" if root_dir == RAW_DIR else "wiki",
                })
    return sources


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    """Divide texto em blocos respeitando quebras de linha/parágrafo."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    pos = 0
    n = len(text)
    while pos < n:
        end = min(pos + max_chars, n)
        if end < n:
            cut = text.rfind("\n", pos + max_chars // 2, end)
            if cut == -1:
                cut = text.rfind(". ", pos + max_chars // 2, end)
            if cut != -1 and cut > pos + max_chars // 2:
                end = cut + 1
        chunks.append(text[pos:end])
        pos = max(end - overlap, pos + max_chars // 2)
    return chunks


def build() -> dict:
    sources = read_sources()
    corpus = []       # [{id, path, title, kind, text}]
    for src in sources:
        chunks = chunk_text(src["text"])
        for i, chunk in enumerate(chunks):
            digest = hashlib.md5(f"{src['path']}#{i}".encode()).hexdigest()[:10]
            corpus.append({
                "id": digest,
                "path": src["path"],
                "title": src["title"],
                "kind": src["kind"],
                "text": chunk,
            })

    # BM25 index
    doc_tokens = [tokenize(c["text"]) for c in corpus]
    N = len(corpus)
    avgdl = sum(len(t) for t in doc_tokens) / max(N, 1)

    df: Counter = Counter()
    for toks in doc_tokens:
        df.update(set(toks))

    postings = {}   # term -> {doc_idx: tf}
    for idx, toks in enumerate(doc_tokens):
        for term, tf in Counter(toks).items():
            postings.setdefault(term, {})[idx] = tf

    index = {
        "version": 1,
        "built": None,
        "N": N,
        "avgdl": avgdl,
        "corpus": corpus,
        "df": dict(df),
        "postings": postings,
    }
    return index


def main() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index = build()
    meta = {
        "version": 1,
        "chunks": index["N"],
        "vocab": len(index["df"]),
        "sources": sorted({c["path"] for c in index["corpus"]}),
    }
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[build_memory] OK: {meta['chunks']} chunks, {meta['vocab']} termos, {len(meta['sources'])} fontes")


if __name__ == "__main__":
    sys.exit(main())
