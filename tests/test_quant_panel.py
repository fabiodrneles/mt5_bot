"""Painel do Modo Quant (tools/quant_runner.py): conteudo, relogio e cache."""
import importlib
import os
import re
import sys

import numpy as np
import MetaTrader5 as mt5

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
qr = importlib.import_module("quant_runner")

_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _snap(**kw):
    snap = {"login": 1, "real": True, "balance": 16.26, "equity": 16.10, "free": 14.35, "today": -0.21,
            "n_trades": 3, "wins": 2, "net": 0.35, "events": [("24/10 22:15", 20, "[HK50] PULLB BUY enviado")],
            "routes": [
                {"symbol": "HK50", "tf": "H4", "setup": "PULLB", "state": "🟢 IN_POSITION (PULLB BUY)",
                 "next_close": "em 1h 05m", "risk": 0.21, "limit": 0.33},
                {"symbol": "US500", "tf": "D1", "setup": "RSI2MR", "state": "🔵 SCANNING",
                 "next_close": "mercado fechado", "risk": 1.62, "limit": 0.33}],
            "positions": [{"symbol": "HK50", "side": "BUY", "volume": 0.01, "open": 23050.0,
                           "sl": 22850.0, "tp": 23450.0, "profit": 0.12}]}
    snap.update(kw)
    return snap


def test_panel_shows_account_routes_locks_and_positions():
    out = _ANSI.sub("", qr.render_panel(_snap(), now="24/10 22:20:00"))
    assert "REAL" in out and "Saldo $16.26" in out
    assert "Placar quant: 3 trades (2 no lucro) · +$0.35" in out
    assert "✓ $0.21 (limite $0.33)" in out          # HK50 cabe no limite
    assert "🔒 $1.62 > limite $0.33" in out         # US500 travado, e o painel diz por que
    assert "HK50 BUY 0.01 @ 23050.00  SL 22850.00  TP 23450.00   +$0.12" in out
    assert "PULLB BUY enviado" in out


def test_panel_empty_state_is_explicit():
    out = _ANSI.sub("", qr.render_panel(_snap(positions=[], events=[])))
    assert "nenhuma — aguardando sinal" in out and "nenhum ainda" in out


def test_next_close_text_uses_server_clock_and_detects_closed_market():
    forming, h4 = 1_000_000, 14400
    assert qr.next_close_text(forming, h4, tick_time=forming + 60, server_now=forming + 120) == "em 3h 58m"
    assert qr.next_close_text(forming, h4, tick_time=forming + 60, server_now=forming + 3 * 86400) == "mercado fechado"
    assert qr.next_close_text(None, h4, tick_time=1, server_now=1) == "—"


def test_candle_cache_refetches_only_when_a_candle_closes(monkeypatch):
    calls = []
    state = {"last": 100_000}

    def rates(symbol, tf, start, count):
        calls.append((start, count))
        if count == 2:
            return np.array([(state["last"],), (state["last"] + 14400,)], dtype=[("time", "i8")])
        t = state["last"] - 14400 * np.arange(count)[::-1]
        return np.array([(x, 1.0, 1.0, 1.0, 1.0) for x in t],
                        dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8")])

    monkeypatch.setattr(mt5, "copy_rates_from_pos", rates)
    cache = qr.CandleCache()
    cache.get("HK50", "H4"); cache.get("HK50", "H4"); cache.get("HK50", "H4")
    assert [c for c in calls if c[1] == 400] == [(1, 400)]  # 3 ciclos, 1 download
    state["last"] += 14400
    df, forming = cache.get("HK50", "H4")
    assert len([c for c in calls if c[1] == 400]) == 2
    assert int(df["time"].iloc[-1].timestamp()) == state["last"] and forming == state["last"] + 14400
