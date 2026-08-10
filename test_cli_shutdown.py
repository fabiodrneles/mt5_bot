import time
import types
import builtins

from main import parse_shutdown_action, wait_until_flat


def test_parse_shutdown_action_valid():
    argv = ["mt5bot", "--shutdown-action", "wait-flat"]
    assert parse_shutdown_action(argv) == "wait-flat"


def test_parse_shutdown_action_missing():
    argv = ["mt5bot"]
    assert parse_shutdown_action(argv) is None


def test_wait_until_flat_success(monkeypatch):
    # Simulate executor returning no positions/orders after a short delay
    calls = {"count": 0}

    def fake_get_positions(symbol):
        calls["count"] += 1
        if calls["count"] > 2:
            return []
        # return a fake position-like object with magic attr
        return [types.SimpleNamespace(magic=123)]

    def fake_get_orders(symbol):
        return []

    import executor as _executor
    import config
    monkeypatch.setattr(config, "MAGIC", 123)
    monkeypatch.setattr(config, "SYMBOLS", ["FAKE"])
    monkeypatch.setattr(_executor, "get_current_positions", fake_get_positions)
    monkeypatch.setattr(_executor, "get_current_orders", fake_get_orders)

    # short timeout but should return True
    assert wait_until_flat(2) is True


def test_wait_until_flat_timeout(monkeypatch):
    # Simulate executor always returning positions -> timeout
    def fake_get_positions(symbol):
        return [types.SimpleNamespace(magic=123)]

    def fake_get_orders(symbol):
        return []

    import executor as _executor
    import config
    monkeypatch.setattr(config, "MAGIC", 123)
    monkeypatch.setattr(config, "SYMBOLS", ["FAKE"])
    monkeypatch.setattr(_executor, "get_current_positions", fake_get_positions)
    monkeypatch.setattr(_executor, "get_current_orders", fake_get_orders)

    assert wait_until_flat(0.5) is False
