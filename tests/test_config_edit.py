"""bot.bat config --edit (spec 003 FR-5)."""
import importlib
import os
import re
import sys

from mt5bot.core import config, user_config

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
show_config = importlib.import_module("show_config")


def _ns():
    import copy
    return {"QUANT_ROUTES": copy.deepcopy(config.QUANT_ROUTES)}


def test_template_changes_nothing_until_uncommented(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(show_config.config_template(), encoding="utf-8")
    ns = _ns()
    assert user_config.apply(ns, str(p)) == [] and ns.get("CONFIG_SOURCES") == {}


def test_every_setting_in_template_is_valid_when_uncommented(tmp_path):
    uncommented = re.sub(r"(?m)^# (\[routes\.\w+\]|\w+ = .+)$", r"\1", show_config.config_template())
    p = tmp_path / "config.toml"
    p.write_text(uncommented, encoding="utf-8")
    ns = _ns()
    assert user_config.apply(ns, str(p)) == []
    for key, spec in user_config.GLOBAL_KEYS.items():  # o modelo documenta todas as chaves aceitas
        if spec[1] == "path":  # caminho depende da maquina: so precisa estar documentado
            assert f"{key} = " in show_config.config_template(), key
            continue
        assert spec[0] in ns["CONFIG_SOURCES"], key


def test_edit_creates_once_and_never_overwrites(tmp_path, monkeypatch):
    target = tmp_path / "config.toml"
    monkeypatch.setattr(config, "USER_CONFIG_FILE", str(target))
    path, created = show_config.edit_config(open_editor=False)
    assert created and target.read_text(encoding="utf-8").startswith("# config.toml do MT5Bot")
    target.write_text("quant_max_risk_pct = 3\n", encoding="utf-8")
    path, created = show_config.edit_config(open_editor=False)
    assert not created and target.read_text(encoding="utf-8") == "quant_max_risk_pct = 3\n"
