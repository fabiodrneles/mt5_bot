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
