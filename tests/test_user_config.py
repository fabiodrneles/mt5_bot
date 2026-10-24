"""Pasta de dados do usuario e config.toml (spec 003)."""
import copy
import importlib
import logging
import os
import sys

from mt5bot.core import config, paths, user_config
from mt5bot.execution import quant_manager

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))


def _ns():
    """Copia do namespace de config.py para aplicar o toml sem mexer no global."""
    return {"QUANT_ROUTES": copy.deepcopy(config.QUANT_ROUTES), "QUANT_MAX_RISK_PCT": 2.0,
            "MAX_DAILY_LOSS_PERCENT": 2.0, "ML_FILTER_ENABLED": True}


def _toml(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_route_override_becomes_effective_limit(tmp_path):  # AC-1
    ns = _ns()
    errors = user_config.apply(ns, _toml(tmp_path, "[routes.US500]\nmax_risk_pct = 5\n"))
    assert errors == []
    assert quant_manager.max_risk_pct(ns["QUANT_ROUTES"]["US500"]) == 5.0
    assert ns["CONFIG_SOURCES"]["QUANT_ROUTES.US500.max_risk_pct"] == "config.toml"


def test_out_of_range_value_is_refused_with_file_and_key(tmp_path, caplog):  # AC-2
    ns = _ns()
    path = _toml(tmp_path, "[routes.US500]\nmax_risk_pct = 500\n")
    with caplog.at_level(logging.WARNING):
        errors = user_config.apply(ns, path)
    assert len(errors) == 1 and path in errors[0] and "routes.US500.max_risk_pct" in errors[0]
    assert ns["QUANT_ROUTES"]["US500"]["max_risk_pct"] == config.QUANT_ROUTES["US500"]["max_risk_pct"]
    assert "recusado" in caplog.text


def test_global_keys_types_unknown_keys_and_disabled_route(tmp_path):
    ns = _ns()
    errors = user_config.apply(ns, _toml(tmp_path, (
        "quant_max_risk_pct = 3\nml_filter_enabled = false\nmax_daily_loss_percent = true\nfoo = 1\n"
        "[routes.HK50]\nenabled = false\n[routes.XYZ]\nmax_risk_pct = 2\n")))
    assert ns["QUANT_MAX_RISK_PCT"] == 3.0 and ns["ML_FILTER_ENABLED"] is False
    assert ns["MAX_DAILY_LOSS_PERCENT"] == 2.0          # bool nao vale como numero
    assert "HK50" not in ns["QUANT_ROUTES"]            # rota desligada
    assert len(errors) == 3                            # bool invalido, 'foo', rota XYZ


def test_invalid_toml_keeps_defaults(tmp_path):
    ns = _ns()
    errors = user_config.apply(ns, _toml(tmp_path, "isto nao e = = toml"))
    assert errors and "arquivo invalido" in errors[0] and ns["QUANT_MAX_RISK_PCT"] == 2.0


def test_missing_file_is_fine(tmp_path):
    ns = _ns()
    assert user_config.apply(ns, str(tmp_path / "nao-existe.toml")) == []
    assert ns["USER_CONFIG_FILE"].endswith("nao-existe.toml")


def test_tests_never_touch_real_user_data():
    real = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "mt5bot")
    assert os.path.normcase(paths.data_dir()) != os.path.normcase(real)
    assert os.path.normcase(config.USER_CONFIG_FILE).startswith(os.path.normcase(paths.data_dir()))


def test_data_dir_per_platform(monkeypatch, tmp_path):
    monkeypatch.delenv("MT5BOT_DATA_DIR")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    assert paths.data_dir() == os.path.join(str(tmp_path), ".local", "share", "mt5bot")
    monkeypatch.setattr(sys, "platform", "darwin")
    assert paths.data_dir() == os.path.join(str(tmp_path), "Library", "Application Support", "mt5bot")
    os.makedirs(tmp_path / ".mt5bot")                # pasta antiga continua valendo
    assert paths.data_dir() == os.path.join(str(tmp_path), ".mt5bot")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    assert paths.data_dir() == os.path.join(str(tmp_path / "AppData"), "mt5bot")


def test_quant_runner_logs_go_to_user_data_dir():  # AC-3
    qr = importlib.import_module("quant_runner")
    qr._setup_logging(plain=True)
    logging.getLogger().info("teste de log")
    for h in logging.getLogger().handlers:
        h.flush()
    log = os.path.join(paths.logs_dir(), "quant_runner.log")
    assert os.path.exists(log) and "teste de log" in open(log, encoding="utf-8").read()
    logging.basicConfig(force=True, handlers=[logging.NullHandler()])


def test_diagnose_counts_recent_errors_in_user_logs():
    diagnose = importlib.import_module("diagnose")
    with open(os.path.join(paths.logs_dir(), "bot_20991231.log"), "w", encoding="utf-8") as f:
        f.write("10:00 [INFO] ok\n10:01 [ERROR] falhou\n10:02 [CRITICAL] parou\n")
    assert diagnose.count_recent_errors() >= 2
