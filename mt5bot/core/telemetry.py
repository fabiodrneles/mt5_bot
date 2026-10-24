"""Telemetria compartilhada pelas interfaces (painel Quant, Maestro e dashboard web).

Uma unica fonte para: conta, posicoes do robo, risco x limite das rotas quant,
contagem ate o proximo candle (relogio do servidor) e estatisticas em US$.
Leve: so chamadas baratas ao MT5 (account_info, positions_get, ticks).
"""
import time

import MetaTrader5 as mt5

from mt5bot.core import config

TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
_CLOCK_SYMBOLS = ("BTCUSD", "ETHUSD")  # negociam 24/7: servem de relogio no fim de semana
_server_offset = None


def account_snapshot():
    acc = mt5.account_info()
    if acc is None:
        return None
    return {"login": getattr(acc, "login", None), "real": getattr(acc, "trade_mode", 0) == 2,
            "balance": float(getattr(acc, "balance", 0.0) or 0.0),
            "equity": float(getattr(acc, "equity", 0.0) or 0.0),
            "margin_free": float(getattr(acc, "margin_free", 0.0) or 0.0),
            "currency": getattr(acc, "currency", "USD")}


def server_now(symbols=()):
    """Horario do servidor (epoch). O fuso e estimado pelo tick mais recente
    (arredondado a 30 min) e guardado: tick.time de um ativo parado nao serve."""
    global _server_offset
    freshest = None
    for s in (*symbols, *(getattr(config, "QUANT_ROUTES", {}) or {}), *_CLOCK_SYMBOLS):
        t = mt5.symbol_info_tick(s)
        if t is not None and getattr(t, "time", None):
            freshest = max(freshest or 0, int(t.time))
    if freshest is not None:
        offset = round((freshest - time.time()) / 1800) * 1800
        if _server_offset is None or offset > _server_offset:
            _server_offset = offset
    return None if _server_offset is None else time.time() + _server_offset


def countdown(secs):
    h, m = divmod(int(secs) // 60, 60)
    return f"em {h}h {m:02d}m" if h else f"em {m}m"


def next_close_text(forming, tf_secs, tick_time, now):
    """Contagem ate o fechamento do candle atual, ou 'mercado fechado'."""
    if forming is None or now is None or not tick_time:
        return "—"
    if now - tick_time > 600:
        return "mercado fechado"
    left = forming + tf_secs - now
    return countdown(left) if left >= 0 else "fechando…"


def route_risk(symbol, route, df, balance):
    """(perda no SL com o lote minimo para um sinal agora, limite da rota) em US$."""
    from mt5bot.engine import quant_setups
    from mt5bot.execution import quant_manager
    limit = balance * quant_manager.max_risk_pct(route) / 100.0
    try:
        atr = float(quant_setups._atr(df).iloc[-1])
        info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
        sl_dist = route.get("params", {}).get("sl_atr", 1.0) * atr
        loss = abs(mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, info.volume_min, tick.bid, tick.bid - sl_dist))
        return round(loss, 2), round(limit, 2)
    except Exception:
        return None, round(limit, 2)


def bot_positions(symbol=None):
    """Posicoes abertas pelo robo (MAGIC). Posicoes manuais ficam de fora."""
    raw = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    out = []
    for p in raw or []:
        if getattr(p, "magic", None) != getattr(config, "MAGIC", 0):
            continue
        comment = str(getattr(p, "comment", "") or "")
        out.append({"ticket": p.ticket, "symbol": p.symbol,
                    "side": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "volume": p.volume, "open": p.price_open, "sl": p.sl, "tp": p.tp,
                    "profit": round(float(p.profit or 0.0), 2),
                    "setup": comment[2:] if comment.startswith(getattr(config, "QUANT_COMMENT_PREFIX", "Q ")) else comment})
    return out


def symbol_telemetry(symbol, timeframe, df):
    """Resumo de um ativo para o Maestro: conta, posicao do robo e rota quant."""
    from mt5bot.execution import quant_manager
    data = {"account": account_snapshot(), "positions": bot_positions(symbol)}
    route = quant_manager.get_route(symbol, timeframe)
    data["validated"] = route is not None
    data["live_allowed"] = route is not None or bool(getattr(config, "ALLOW_UNVALIDATED_LIVE", False))
    tf_secs = TF_SECONDS.get(str(timeframe).upper())
    if tf_secs:
        forming = mt5.copy_rates_from_pos(symbol, quant_manager.TF_CONST[tf_secs], 0, 1)
        tick = mt5.symbol_info_tick(symbol)
        data["next_close"] = next_close_text(
            int(forming[-1]["time"]) if forming is not None and len(forming) else None,
            tf_secs, int(getattr(tick, "time", 0) or 0), server_now((symbol,)))
    if route:
        balance = (data["account"] or {}).get("balance", 0.0)
        risk, limit = route_risk(symbol, route, df, balance)
        data["quant"] = {"setup": route["setup"], "risk": risk, "limit": limit}
    return data


def trade_stats(trades):
    """Estatisticas em US$ dos trades fechados (pnl_money = lucro real do MT5)."""
    closed = [t for t in trades if t.get("result") in ("win", "loss", "breakeven")]
    pnl = [float(t.get("pnl_money") or 0.0) for t in closed]
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p < 0]
    curve, peak, dd, acc = [], 0.0, 0.0, 0.0
    for t, p in zip(closed, pnl):
        acc += p
        peak = max(peak, acc)
        dd = max(dd, peak - acc)
        curve.append({"time": t.get("exit_time") or t.get("entry_time"), "equity": round(acc, 2)})
    gl = -sum(losses)
    return {"trades": len(pnl), "wins": len(wins), "losses": len(losses),
            "net": round(sum(pnl), 2), "win_rate": round(100 * len(wins) / len(pnl), 1) if pnl else 0.0,
            "profit_factor": round(sum(wins) / gl, 2) if gl > 0 else None,
            "max_drawdown": round(dd, 2), "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0, "curve": curve}


def group_stats(trades, key):
    """trade_stats agrupado por 'symbol' ou 'setup' (sem a curva)."""
    groups = {}
    for t in trades:
        groups.setdefault(t.get(key) or "—", []).append(t)
    out = {}
    for k, ts in sorted(groups.items()):
        s = trade_stats(ts)
        if s["trades"]:
            s.pop("curve")
            out[k] = s
    return out
