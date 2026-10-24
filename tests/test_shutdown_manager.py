"""/quit do Maestro: so pode mexer no que e do robo (MAGIC).

Antes o close-all fechava TODAS as posicoes da conta (inclusive as manuais),
cancelava ordens manuais, e o wait-flat nunca terminava com uma posicao
manual aberta.
"""
import MetaTrader5 as mt5

from mt5bot.core import config, shutdown_manager as sm


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _env(monkeypatch, positions, orders):
    sent = []
    monkeypatch.setattr(mt5, "positions_get", lambda **k: list(positions))
    monkeypatch.setattr(mt5, "orders_get", lambda **k: list(orders))
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=100.0, ask=100.5))
    monkeypatch.setattr(mt5, "ORDER_TIME_GTC", 0, raising=False)
    monkeypatch.setattr(mt5, "order_send", lambda r: sent.append(r) or _Obj(retcode=mt5.TRADE_RETCODE_DONE))
    return sent


def test_close_all_spares_manual_positions_and_orders(monkeypatch):
    bot = _Obj(ticket=1, symbol="HK50", volume=0.01, type=mt5.POSITION_TYPE_BUY, magic=config.MAGIC)
    manual = _Obj(ticket=2, symbol="HK50", volume=0.01, type=mt5.POSITION_TYPE_BUY, magic=0)
    bot_order = _Obj(ticket=3, symbol="HK50", magic=config.MAGIC)
    manual_order = _Obj(ticket=4, symbol="HK50", magic=0)
    sent = _env(monkeypatch, [bot, manual], [bot_order, manual_order])

    sm.cancel_pending_orders()
    sm.close_all_positions()

    assert [r.get("order") for r in sent if r["action"] == mt5.TRADE_ACTION_REMOVE] == [3]
    assert [r["position"] for r in sent if r["action"] == mt5.TRADE_ACTION_DEAL] == [1]


def test_wait_flat_ignores_manual_positions(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    manual = _Obj(ticket=2, symbol="HK50", volume=0.01, type=mt5.POSITION_TYPE_BUY, magic=0)
    _env(monkeypatch, [manual], [])
    monkeypatch.setattr(sm.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("ficou esperando")))

    sm.wait_flat()  # termina sem esperar: nao ha posicao do robo
