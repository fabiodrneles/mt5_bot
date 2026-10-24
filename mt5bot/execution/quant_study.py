"""Rotas quant em ESTUDO (route["mode"] == "study"): mesmo sinal, mesmo horario de entrada e mesma regra de
saida da rota ao vivo, mas a posicao e VIRTUAL. Nada e enviado ao MT5.

Serve para acumular historico ao vivo de uma rota validada que ainda nao cabe na conta (ex.: US100 D1 RSI2MR
com $16; ver cap. 14 do guia) ou que esta na faixa experimental do protocolo de pesquisa. As posicoes ficam
em <dados>/quant_study.json e o resultado e medido no lote minimo com order_calc_profit (comissao e swap nao
entram: o estudo mede o sinal; a rota ao vivo mede o dinheiro).
"""
import json
import logging
import os
from datetime import datetime, timezone

import MetaTrader5 as mt5

from mt5bot.core import paths
from mt5bot.engine import quant_setups
from mt5bot.execution import quant_manager as Q

STUDY_FILE = "quant_study.json"
PREFIX = "📘 ESTUDO"


def _path():
    return paths.data_file(STUDY_FILE)


def load():
    try:
        with open(_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(trades):
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(trades, fh, indent=1)
    os.replace(tmp, _path())


def _usd(symbol, side, entry, exit_price):
    info = mt5.symbol_info(symbol)
    order = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    value = mt5.order_calc_profit(order, symbol, getattr(info, "volume_min", 0.01), entry, exit_price)
    return round(float(value), 4) if value is not None else None


def study_cycle(symbol, df, timeframe_name, route):
    setup, params = route["setup"], route.get("params", {})
    tf_secs = Q.TF_SECONDS.get(str(timeframe_name).upper(), 3600)
    trades = load()
    open_trade = next((t for t in trades if t["symbol"] == symbol and t["status"] == "open"), None)
    if open_trade:
        return _manage(symbol, df, setup, params, tf_secs, trades, open_trade)
    return _scan(symbol, df, setup, params, tf_secs, trades)


def _manage(symbol, df, setup, params, tf_secs, trades, t):
    is_buy = t["side"] == "BUY"
    times = [Q._bar_epoch(x) for x in df["time"]]
    after = [i for i, x in enumerate(times) if x >= t["entry_bar"]]  # candles FECHADOS desde a entrada
    reason, exit_price = None, None
    for i in after:  # stop/alvo tocados em algum candle fechado (stop primeiro: hipotese pessimista)
        lo, hi = float(df["low"].iloc[i]), float(df["high"].iloc[i])
        if (is_buy and lo <= t["sl"]) or (not is_buy and hi >= t["sl"]):
            reason, exit_price = "stop", t["sl"]
            break
        if t.get("tp") and ((is_buy and hi >= t["tp"]) or (not is_buy and lo <= t["tp"])):
            reason, exit_price = "alvo", t["tp"]
            break
    if reason is None and after and quant_setups.should_exit(setup, df, is_buy, params):
        reason, exit_price = "regra de saida", float(df["close"].iloc[-1])
    max_bars = params.get("max_bars")
    if reason is None and max_bars and len(after) >= max_bars:
        reason, exit_price = "tempo", float(df["close"].iloc[-1])
    if reason is None:
        return f"{PREFIX}: POSIÇÃO VIRTUAL ({setup} {t['side']})"
    t.update(status="closed", exit_price=exit_price, exit_reason=reason,
             exit_time=datetime.now(tz=timezone.utc).isoformat(),
             result_usd=_usd(symbol, t["side"], t["entry_price"], exit_price))
    _save(trades)
    logging.info(f"[{symbol}] {setup} (estudo): saida virtual por {reason} a {exit_price}; "
                 f"resultado no lote minimo ${t['result_usd']}")
    return f"{PREFIX}: SAÍDA VIRTUAL ({reason})"


def _scan(symbol, df, setup, params, tf_secs, trades):
    if df is None or len(df) < 200:
        return f"{PREFIX}: AGUARDANDO DADOS"
    last_time = df["time"].iloc[-1]
    if Q._last_signal_candle.get(symbol) == last_time:
        return f"{PREFIX}: AGUARDANDO PRÓXIMO CANDLE"
    sig = quant_setups.evaluate(setup, df, params)
    if sig is None:
        Q._last_signal_candle[symbol] = last_time
        return f"{PREFIX}: SCANNING"
    waiting, tick, _ = Q.entry_window(symbol, setup, last_time, tf_secs)
    if waiting:
        return f"{PREFIX}: {waiting}"
    Q._last_signal_candle[symbol] = last_time
    is_buy = sig["action"] == "buy"
    price = tick.ask if is_buy else tick.bid
    sl = price - sig["sl_dist"] if is_buy else price + sig["sl_dist"]
    tp = None
    if sig.get("tp_dist"):
        tp = price + sig["tp_dist"] if is_buy else price - sig["tp_dist"]
    side = "BUY" if is_buy else "SELL"
    trades.append(dict(id=len(trades) + 1, symbol=symbol, setup=setup, side=side, status="open",
                       entry_time=datetime.now(tz=timezone.utc).isoformat(),
                       entry_bar=Q._bar_epoch(last_time) + tf_secs, entry_price=price, sl=sl, tp=tp,
                       risk_usd=abs(_usd(symbol, side, price, sl) or 0.0)))
    _save(trades)
    logging.info(f"[{symbol}] {setup} (estudo): entrada VIRTUAL {side} a {price} SL {sl:.2f}; nenhuma ordem enviada.")
    return f"{PREFIX}: ENTRADA VIRTUAL ({setup} {side})"


def summary(symbol=None):
    """Trades de estudo encerrados: quantidade, acerto e resultado no lote minimo."""
    done = [t for t in load() if t["status"] == "closed" and (symbol is None or t["symbol"] == symbol)
            and t.get("result_usd") is not None]
    wins = sum(t["result_usd"] > 0 for t in done)
    return dict(n=len(done), wins=wins, net=round(sum(t["result_usd"] for t in done), 2),
                open=sum(t["status"] == "open" and (symbol is None or t["symbol"] == symbol) for t in load()))
