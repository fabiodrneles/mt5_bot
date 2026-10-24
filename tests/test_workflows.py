"""Guarda-corpos dos workflows do GitHub Actions (spec 005 FR-1)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    with open(os.path.join(ROOT, ".github", "workflows", name), encoding="utf-8") as f:
        return f.read()


def test_ml_training_runs_only_on_demand_and_cannot_write_to_repo():
    wf = _read("ml_training.yml")
    on_block = wf.split("\non:", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch" in on_block and "push" not in on_block   # "HTML" no commit nao dispara
    assert "contents: read" in wf and "contents: write" not in wf
    assert "git push" not in wf and "head_commit.message" not in wf
