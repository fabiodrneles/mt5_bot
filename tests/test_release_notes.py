"""Notas da release a partir do CHANGELOG (spec 002 FR-5)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
rn = importlib.import_module("release_notes")

CHANGELOG = """# Changelog

## [Unreleased]

## [2.14.0] - 2026-10-25
### Adicionado
- Instalador Windows.

## [2.13.0] - 2026-10-24
- Fase 1.
"""


def test_extracts_only_the_requested_version():
    assert rn.notes_for("2.14.0", CHANGELOG) == "### Adicionado\n- Instalador Windows."
    assert rn.notes_for("2.13.0", CHANGELOG) == "- Fase 1."


def test_missing_version_is_an_error():
    assert rn.notes_for("9.9.9", CHANGELOG) is None
    assert rn.main(["release_notes.py", "v9.9.9"]) == 1


def test_real_changelog_has_current_release():
    assert rn.main(["release_notes.py", "v2.13.0"]) == 0
