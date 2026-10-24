"""Telemetria compartilhada (mt5bot/core/telemetry.py)."""
import MetaTrader5 as mt5

from mt5bot.core import config, telemetry


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_bot_positions_excludes_manual_and_strips_quant_prefix(monkeypatch):
    bot = _Obj(ticket=1, symbol="HK50", type=mt5.POSITION_TYPE_BUY, magic=config.MAGIC, comment="Q PULLB",
               volume=0.01, price_open=23000.0, sl=22800.0, tp=23400.0, profit=0.123)
    manual = _Obj(ticket=2, symbol="HK50", type=mt5.POSITION_TYPE_BUY, magic=0, comment="",
                  volume=0.01, price_open=24380.0, sl=0.0, tp=0.0, profit=-1.63)
    monkeypatch.setattr(mt5, "positions_get", lambda **k: [bot, manual])

    out = telemetry.bot_positions("HK50")

    assert [p["ticket"] for p in out] == [1]
    assert out[0]["setup"] == "PULLB" and out[0]["side"] == "BUY" and out[0]["profit"] == 0.12


def test_trade_stats_in_dollars_with_drawdown_and_curve():
    trades = [{"result": "win", "pnl_money": 0.40}, {"result": "loss", "pnl_money": -0.20},
              {"result": "loss", "pnl_money": -0.30}, {"result": "win", "pnl_money": 0.50},
              {"result": "open", "pnl_money": None}]

    s = telemetry.trade_stats(trades)

    assert (s["trades"], s["wins"], s["losses"]) == (4, 2, 2)
    assert s["net"] == 0.40 and s["win_rate"] == 50.0
    assert s["profit_factor"] == 1.8 and s["max_drawdown"] == 0.50
    assert [c["equity"] for c in s["curve"]] == [0.40, 0.20, -0.10, 0.40]


def test_group_stats_by_setup():
    trades = [{"result": "win", "pnl_money": 0.4, "setup": "PULLB"},
              {"result": "loss", "pnl_money": -1.6, "setup": "RSI2MR"}]
    g = telemetry.group_stats(trades, "setup")
    assert g["PULLB"]["net"] == 0.4 and g["RSI2MR"]["net"] == -1.6 and "curve" not in g["PULLB"]


def test_trade_stats_empty():
    s = telemetry.trade_stats([])
    assert s["trades"] == 0 and s["profit_factor"] is None and s["curve"] == []
