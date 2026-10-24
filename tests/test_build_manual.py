"""Guia tecnico em arquivo unico gerado a partir de docs/manual."""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
bm = importlib.import_module("build_manual")


def test_order_readme_chapters_appendices_references():
    names = ["referencias.md", "12-motores.md", "apendice-a-glossario.md", "README.md", "00-fundamentos.md", "x.txt"]
    assert bm.chapter_order(names) == [
        "README.md", "00-fundamentos.md", "12-motores.md", "apendice-a-glossario.md", "referencias.md"]


def test_links_between_chapters_become_anchors():
    chapters = {"01-arquitetura.md", "referencias.md"}
    text = "[cap. 1](01-arquitetura.md), [refs](referencias.md#x), [spec](../../specs/ANALYSIS.md), [web](https://a.b)"
    assert bm.rewrite_links(text, chapters) == (
        "[cap. 1](#01-arquitetura), [refs](#x), [spec](specs/ANALYSIS.md), [web](https://a.b)")


def test_real_manual_builds_with_every_chapter(tmp_path):
    out = tmp_path / "guia.md"
    assert bm.main(["build_manual.py", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    for name in os.listdir(bm.MANUAL):
        if name.endswith(".md"):
            assert f'<a id="{name[:-3]}"></a>' in text
            assert f"]({name}" not in text
    assert "](../../" not in text


def test_figures_are_embedded(tmp_path):
    (tmp_path / "img").mkdir()
    (tmp_path / "img" / "a.png").write_bytes(b"\x89PNG")
    out = bm.embed_images("![Fig](img/a.png) ![x](img/falta.png)", str(tmp_path))
    assert out == "![Fig](data:image/png;base64,iVBORw==) ![x](img/falta.png)"
