"""Executor headless das rotas quant (config.QUANT_ROUTES) com painel ao vivo.

Uso:
    python tools\\quant_runner.py            # painel ao vivo (Ctrl+C para parar)
    python tools\\quant_runner.py --plain    # so linhas de log (bom para redirecionar)
    python tools\\quant_runner.py --once     # um ciclo por rota, mostra o painel e sai

Faz o mesmo que o Maestro faria com `/add HK50 H4` e `/add US500 D1`: puxa as
velas FECHADAS do MT5 e chama execution_manager.manage_cycle, que despacha para
o caminho quant. As 400 velas so sao baixadas de novo quando fecha um candle;
entre um fechamento e outro o ciclo reaproveita o cache (leve para i3/4GB).
"""
import argparse
import collections
import logging
import os
import sys
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import MetaTrader5 as mt5
import pandas as pd

from mt5bot.core import config
from mt5bot.data import tracker
from mt5bot.engine import quant_setups
from mt5bot.execution import execution_manager, quant_manager

TF_MAP = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
TF_SECS = quant_manager.TF_SECONDS

# Eventos relevantes para o painel (o log completo fica em logs/quant_runner.log).
_EVENTS = collections.deque(maxlen=6)
_NOISE = ("sem sinal no candle",)


class _EventHandler(logging.Handler):
    def emit(self, record):
        msg = record.getMessage()
        if record.levelno >= logging.INFO and not any(n in msg for n in _NOISE):
            _EVENTS.append((datetime.now().strftime("%d/%m %H:%M"), record.levelno, msg))


def _setup_logging(plain):
    # Console do Windows (cp1252) nao imprime os emojis de estado.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    handlers = [logging.FileHandler(os.path.join(_ROOT, "logs", "quant_runner.log"), encoding="utf-8"),
                _EventHandler()]
    if plain:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                        handlers=handlers, force=True)


# --- dados ---------------------------------------------------------------------

class CandleCache:
    """Baixa 400 velas fechadas so quando o ultimo candle fechado muda."""

    def __init__(self):
        self._df = {}

    def get(self, symbol, timeframe):
        """Retorna (df de velas fechadas, epoch de abertura do candle em formacao)."""
        head = mt5.copy_rates_from_pos(symbol, TF_MAP[timeframe], 0, 2)
        if head is None or len(head) < 2:
            return None, None
        last_closed, forming = int(head[0]["time"]), int(head[1]["time"])
        cached = self._df.get(symbol)
        if cached is None or int(cached["time"].iloc[-1].timestamp()) != last_closed:
            rates = mt5.copy_rates_from_pos(symbol, TF_MAP[timeframe], 1, 400)
            if rates is None or len(rates) == 0:
                return None, forming
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            self._df[symbol] = cached = df
        return cached, forming


def _risk_estimate(symbol, route, df, balance):
    """Perda no SL com o lote minimo para um sinal agora e o limite da rota."""
    limit = balance * quant_manager.max_risk_pct(route) / 100.0
    try:
        atr = float(quant_setups._atr(df).iloc[-1])
        info, tick = mt5.symbol_info(symbol), mt5.symbol_info_tick(symbol)
        sl_dist = route.get("params", {}).get("sl_atr", 1.0) * atr
        loss = abs(mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, info.volume_min, tick.bid, tick.bid - sl_dist))
        return loss, limit
    except Exception:
        return None, limit


_CLOCK_SYMBOLS = ("BTCUSD", "ETHUSD")  # negociam 24/7: servem de relogio no fim de semana
_server_offset = None


def _server_now():
    """Horario do servidor (epoch). O fuso do servidor e estimado pelo tick mais
    recente (arredondado a 30 min) e guardado; tick.time de um ativo parado nao
    serve de relogio."""
    global _server_offset
    ticks = [mt5.symbol_info_tick(s) for s in (*config.QUANT_ROUTES, *_CLOCK_SYMBOLS)]
    freshest = max((int(t.time) for t in ticks if t is not None and getattr(t, "time", None)), default=None)
    if freshest is not None:
        offset = round((freshest - time.time()) / 1800) * 1800
        if _server_offset is None or offset > _server_offset:
            _server_offset = offset
    return None if _server_offset is None else time.time() + _server_offset


def next_close_text(forming, tf_secs, tick_time, server_now):
    """Contagem ate o fechamento do candle atual, ou 'mercado fechado'."""
    if forming is None or server_now is None or not tick_time:
        return "—"
    if server_now - tick_time > 600:
        return "mercado fechado"
    left = forming + tf_secs - server_now
    return _countdown(left) if left >= 0 else "fechando…"


def collect_snapshot(states, cache_info):
    acc = mt5.account_info()
    setups = {r["setup"] for r in config.QUANT_ROUTES.values()}
    closed = [t for t in tracker.get_closed_trades() if t.get("setup") in setups]
    pnl = [float(t.get("pnl_money") or 0.0) for t in closed]
    snap = {
        "login": getattr(acc, "login", "?"), "real": getattr(acc, "trade_mode", 0) == 2,
        "balance": float(getattr(acc, "balance", 0.0) or 0.0), "equity": float(getattr(acc, "equity", 0.0) or 0.0),
        "free": float(getattr(acc, "margin_free", 0.0) or 0.0),
        "today": float(tracker.get_daily_pnl() or 0.0),
        "n_trades": len(pnl), "wins": sum(p > 0 for p in pnl), "net": sum(pnl),
        "routes": [], "positions": [], "events": list(_EVENTS),
    }
    server_now = _server_now()
    for symbol, route in config.QUANT_ROUTES.items():
        df, forming = cache_info.get(symbol, (None, None))
        tick = mt5.symbol_info_tick(symbol)
        next_close = next_close_text(forming, TF_SECS[route["timeframe"]],
                                     int(getattr(tick, "time", 0) or 0), server_now)
        loss, limit = _risk_estimate(symbol, route, df, snap["balance"]) if df is not None else (None, None)
        snap["routes"].append({"symbol": symbol, "tf": route["timeframe"], "setup": route["setup"],
                               "state": states.get(symbol, "…"), "next_close": next_close,
                               "risk": loss, "limit": limit})
        for p in mt5.positions_get(symbol=symbol) or []:
            if quant_manager.is_quant_position(p):
                snap["positions"].append({"symbol": symbol, "side": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                                          "volume": p.volume, "open": p.price_open, "sl": p.sl, "tp": p.tp,
                                          "profit": float(p.profit or 0.0)})
    return snap


# --- painel --------------------------------------------------------------------

_C = {"dim": "\x1b[2m", "b": "\x1b[1m", "g": "\x1b[32m", "r": "\x1b[31m", "y": "\x1b[33m",
      "o": "\x1b[38;5;208m", "x": "\x1b[0m"}


def _money(v, color=True):
    s = f"{'+' if v > 0 else ''}${v:.2f}" if v else "$0.00"
    if not color or not v:
        return s
    return f"{_C['g'] if v > 0 else _C['r']}{s}{_C['x']}"


def _countdown(secs):
    h, m = divmod(int(secs) // 60, 60)
    return f"em {h}h {m:02d}m" if h else f"em {m}m"


def render_panel(snap, now=None):
    now = now or datetime.now().strftime("%d/%m %H:%M:%S")
    line = f"{_C['dim']}{'─' * 78}{_C['x']}"
    acc = (f"{_C['r'] + 'REAL' if snap['real'] else _C['g'] + 'DEMO'}{_C['x']}")
    out = [f"{_C['o']}{_C['b']} MT5Bot · Modo Quant{_C['x']}{' ' * 44}{_C['dim']}{now}{_C['x']}", line,
           f" Conta {snap['login']} {acc}   Saldo ${snap['balance']:.2f}   Patrimônio ${snap['equity']:.2f}"
           f"   Margem livre ${snap['free']:.2f}",
           f" Hoje {_money(snap['today'])}   Placar quant: {snap['n_trades']} trades"
           f" ({snap['wins']} no lucro) · {_money(snap['net'])}", "",
           f"{_C['b']} {'ROTA':18}{'ESTADO':28}{'PRÓX. CANDLE':17}RISCO POR TRADE{_C['x']}"]
    for r in snap["routes"]:
        if r["risk"] is None:
            risk = "—"
        elif r["risk"] <= r["limit"]:
            risk = f"{_C['g']}✓ ${r['risk']:.2f}{_C['x']} (limite ${r['limit']:.2f})"
        else:
            risk = f"{_C['y']}🔒 ${r['risk']:.2f} > limite ${r['limit']:.2f}{_C['x']}"
        name = f"{r['symbol']} {r['tf']} {r['setup']}"
        out.append(f" {name:18}{r['state'][:26]:28}{r['next_close']:17}{risk}")
    out += ["", f"{_C['b']} POSIÇÕES DO ROBÔ{_C['x']}"]
    if not snap["positions"]:
        out.append(f"{_C['dim']}   nenhuma — aguardando sinal{_C['x']}")
    for p in snap["positions"]:
        tp = f"  TP {p['tp']:.2f}" if p["tp"] else ""
        out.append(f"   {p['symbol']} {p['side']} {p['volume']} @ {p['open']:.2f}  SL {p['sl']:.2f}{tp}   {_money(p['profit'])}")
    out += ["", f"{_C['b']} EVENTOS{_C['x']}"]
    if not snap["events"]:
        out.append(f"{_C['dim']}   nenhum ainda{_C['x']}")
    for t, lvl, msg in snap["events"]:
        color = _C["r"] if lvl >= logging.ERROR else _C["y"] if lvl >= logging.WARNING else ""
        out.append(f"   {_C['dim']}{t}{_C['x']} {color}{msg[:66]}{_C['x'] if color else ''}")
    out += [line, f"{_C['dim']} Ctrl+C para parar · emergência: .\\bot.bat panic · log: logs\\quant_runner.log{_C['x']}"]
    return "\n".join(out)


# --- loop ----------------------------------------------------------------------

def run(once=False, interval=5, plain=False):
    if not mt5.initialize():
        logging.error(f"Falha ao conectar no MT5: {mt5.last_error()}")
        print(f"Falha ao conectar no MT5: {mt5.last_error()}. Abra o terminal e faca login.")
        return 1
    acc = mt5.account_info()
    logging.info(f"Quant runner conectado: conta {acc.login} ({'REAL' if acc.trade_mode == 2 else 'DEMO'}) "
                 f"saldo ${acc.balance:.2f} | rotas: "
                 + ", ".join(f"{s} {r['timeframe']} {r['setup']}" for s, r in config.QUANT_ROUTES.items()))
    if not plain:
        os.system("")  # liga as cores ANSI no console do Windows
    cache = CandleCache()
    states, last_logged = {}, {}
    while True:
        cache_info = {}
        for symbol, route in config.QUANT_ROUTES.items():
            try:
                mt5.symbol_select(symbol, True)
                df, forming = cache.get(symbol, route["timeframe"])
                cache_info[symbol] = (df, forming)
                state = "🔴 SEM DADOS" if df is None else execution_manager.manage_cycle(
                    symbol, df, timeframe_name=route["timeframe"])
            except Exception as e:
                logging.exception(f"[{symbol}] Erro no ciclo quant: {e}")
                state = "🔴 ERRO"
            states[symbol] = state
            if once or last_logged.get(symbol) != state:
                logging.info(f"[{symbol} {route['timeframe']}] {state}")
                last_logged[symbol] = state
        if not plain:
            try:
                panel = render_panel(collect_snapshot(states, cache_info))
                sys.stdout.write("\x1b[H\x1b[2J" + panel + "\n")
                sys.stdout.flush()
            except Exception as e:
                logging.warning(f"Falha ao desenhar o painel: {e}")
        if once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="um ciclo e sai")
    ap.add_argument("--plain", action="store_true", help="so log, sem painel")
    ap.add_argument("--interval", type=int, default=5)
    args = ap.parse_args()
    plain = args.plain or not sys.stdout.isatty()
    _setup_logging(plain)
    try:
        sys.exit(run(once=args.once, interval=args.interval, plain=plain))
    except KeyboardInterrupt:
        logging.info("Quant runner encerrado pelo usuario.")
        print("\nQuant runner encerrado. As posicoes abertas continuam com SL/TP no MT5.")
