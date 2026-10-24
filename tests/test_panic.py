"""bot.bat panic: precisa fechar as posicoes com o MAGIC real do bot.

Antes lia config.MAGIC_NUMBER (inexistente -> 999) e, numa emergencia,
respondia "nenhuma posicao do robo" sem fechar nada.
"""
import importlib
import os
import sys

import MetaTrader5 as mt5

from mt5bot.core import config

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_panic_closes_bot_positions_and_spares_manual(monkeypatch):
    panic = importlib.import_module("panic")
    bot = _Obj(ticket=1, symbol="HK50", volume=0.01, type=mt5.POSITION_TYPE_BUY, magic=config.MAGIC)
    manual = _Obj(ticket=2, symbol="HK50", volume=0.01, type=mt5.POSITION_TYPE_BUY, magic=0)
    sent = []
    monkeypatch.setattr(mt5, "positions_get", lambda **k: [bot, manual])
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: _Obj(bid=100.0, ask=100.5))
    monkeypatch.setattr(mt5, "ORDER_TIME_GTC", 0, raising=False)
    monkeypatch.setattr(mt5, "order_send", lambda r: sent.append(r) or _Obj(retcode=mt5.TRADE_RETCODE_DONE))

    panic.run_panic()

    assert [r["position"] for r in sent] == [1]
    assert sent[0]["magic"] == config.MAGIC and sent[0]["type"] == mt5.ORDER_TYPE_SELL
