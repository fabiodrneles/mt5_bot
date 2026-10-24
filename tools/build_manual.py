"""Junta o manual tecnico (docs/manual) num arquivo unico, para estudo e para a release.

Uso:  python tools/build_manual.py [saida.md]
Padrao: dist/MT5Bot-Guia-Tecnico-<versao>.md. Os links entre capitulos viram
ancoras internas, as figuras sao embutidas (data URI) para o arquivo ser autossuficiente,
e os caminhos fora do manual ficam relativos a raiz do repositorio.
"""
import base64
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(ROOT, "docs", "manual")


def chapter_order(names):
    """README primeiro, capitulos numerados, apendices e, por fim, as referencias."""
    def key(name):
        if name == "README.md":
            return (0, name)
        if name == "referencias.md":
            return (3, name)
        if name.startswith("apendice"):
            return (2, name)
        return (1, name)
    return sorted((n for n in names if n.endswith(".md")), key=key)


def rewrite_links(text, chapters):
    def repl(m):
        label, target = m.group(1), m.group(2)
        page, _, frag = target.partition("#")
        if page in chapters:
            return f"[{label}](#{frag or page[:-3]})"
        if page.startswith("../../"):
            return f"[{label}]({target[len('../../'):]})"
        return m.group(0)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", repl, text)


def embed_images(text, manual_dir):
    def repl(m):
        path = os.path.join(manual_dir, m.group(2))
        if not os.path.isfile(path):
            return m.group(0)
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"![{m.group(1)}](data:image/png;base64,{data})"
    return re.sub(r"!\[([^\]]*)\]\(([^)\s]+\.png)\)", repl, text)


def version():
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        return re.search(r'^version = "([^"]+)"', f.read(), re.M).group(1)


def build(manual_dir=MANUAL, ver=None):
    names = chapter_order(os.listdir(manual_dir))
    parts = [f"# MT5Bot: guia técnico completo (v{ver or version()})\n\n"
             "> Arquivo gerado por `tools/build_manual.py` a partir de `docs/manual/`. "
             "Caminhos de código são relativos à raiz do repositório.\n"]
    for name in names:
        with open(os.path.join(manual_dir, name), encoding="utf-8") as f:
            text = embed_images(rewrite_links(f.read().strip(), set(names)), manual_dir)
        if name == "README.md":
            text = re.sub(r"^# .*\n", "", text, count=1)
        parts.append(f'<a id="{name[:-3]}"></a>\n\n{text}\n')
    return "\n---\n\n".join(parts)


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(ROOT, "dist", f"MT5Bot-Guia-Tecnico-{version()}.md")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(build())
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
