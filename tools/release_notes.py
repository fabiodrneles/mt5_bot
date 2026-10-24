"""Extrai do CHANGELOG.md as notas de uma versao (usado pelo workflow de release).

Uso:  python tools/release_notes.py 2.14.0 > notes.md
Sai com codigo 1 se a versao nao estiver no CHANGELOG (release sem notas = erro).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def notes_for(version, text):
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else None


def main(argv):
    version = argv[1].lstrip("v")
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        notes = notes_for(version, f.read())
    if not notes:
        print(f"CHANGELOG.md nao tem a secao [{version}]", file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
