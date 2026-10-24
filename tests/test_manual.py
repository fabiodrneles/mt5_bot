"""O manual tecnico (docs/manual) nao pode apodrecer: citacoes e caminhos validos."""
import glob
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(ROOT, "docs", "manual")


def _chapters():
    return {os.path.basename(f): io.open(f, encoding="utf-8").read()
            for f in sorted(glob.glob(os.path.join(MANUAL, "*.md")))}


def _reference_keys():
    refs = io.open(os.path.join(MANUAL, "referencias.md"), encoding="utf-8").read()
    return set(re.findall(r"\*\*\[([^\]]+)\]\*\*", refs))


def test_every_citation_has_a_reference():
    keys = _reference_keys()
    missing = []
    for name, text in _chapters().items():
        if name == "referencias.md":
            continue
        for group in re.findall(r"\[([A-Z][^\]\[]*?(?:\d{4}|Fernandes)[^\]\[]*?)\]", text):
            for key in (k.strip() for k in group.split(";")):
                key = re.sub(r",? cap\..*$", "", key).strip()
                if (re.search(r"\d{4}", key) or key.startswith("Fernandes")) and key not in keys:
                    missing.append((name, key))
    assert missing == []


def test_every_reference_is_cited():
    text = "".join(t for n, t in _chapters().items() if n != "referencias.md")
    assert [k for k in _reference_keys() if f"{k}" not in text] == []


def test_code_paths_cited_in_manual_exist():
    paths = set()
    for text in _chapters().values():
        paths |= set(re.findall(
            r"`((?:mt5bot|interfaces|tools|maestro|packaging|memoria|specs|tests)/[\w./-]+?)`", text))
    assert paths and [p for p in sorted(paths) if not os.path.exists(os.path.join(ROOT, p.rstrip("/")))] == []


def test_code_listings_match_the_source():
    """Cada 'Listagem N.M — caminho' tem de existir no arquivo, linha a linha e na ordem
    ('...' marca trechos omitidos)."""
    stale = []
    for name, text in _chapters().items():
        for block in re.findall(r"```\w*\n(.*?)```", text, re.S):
            lines = block.rstrip("\n").split("\n")
            m = re.match(r"\s*(?:#|//) Listagem [\d.]+ — (\S+)", lines[0])
            if not m:
                continue
            source = [ln.strip() for ln in io.open(os.path.join(ROOT, m.group(1)), encoding="utf-8").read().splitlines()]
            pos = 0
            for line in (ln.strip() for ln in lines[1:]):
                if not line or line == "...":
                    continue
                try:
                    pos = source.index(line, pos) + 1
                except ValueError:
                    stale.append((name, m.group(1), line))
                    break
    assert stale == []


def test_figures_exist():
    missing = [(n, p) for n, t in _chapters().items()
               for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", t) if not os.path.exists(os.path.join(MANUAL, p))]
    assert missing == []
