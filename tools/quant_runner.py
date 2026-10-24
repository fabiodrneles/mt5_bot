"""Executor headless das rotas quant (config.QUANT_ROUTES) com painel ao vivo.

Uso:
    python tools\\quant_runner.py            # painel ao vivo colorido (Ctrl+C para parar)
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
import re
import sys
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import MetaTrader5 as mt5
import pandas as pd

from mt5bot.core import config, telemetry
from mt5bot.core import terminal
from mt5bot.data import tracker
from mt5bot.execution import execution_manager, quant_manager

TF_MAP = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
TF_SECS = telemetry.TF_SECONDS
WIDTH = 80

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
    from mt5bot.core import paths
    handlers = [logging.FileHandler(os.path.join(paths.logs_dir(), "quant_runner.log"), encoding="utf-8"),
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


def collect_snapshot(states, cache_info):
    acc = telemetry.account_snapshot() or {}
    setups = {r["setup"] for r in config.QUANT_ROUTES.values()}
    stats = telemetry.trade_stats([t for t in tracker.get_closed_trades() if t.get("setup") in setups])
    snap = {
        "login": acc.get("login", "?"), "real": acc.get("real", False),
        "balance": acc.get("balance", 0.0), "equity": acc.get("equity", 0.0), "free": acc.get("margin_free", 0.0),
        "today": float(tracker.get_daily_pnl() or 0.0),
        "n_trades": stats["trades"], "wins": stats["wins"], "net": stats["net"],
        "routes": [], "positions": [], "events": list(_EVENTS),
    }
    now = telemetry.server_now()
    for symbol, route in config.QUANT_ROUTES.items():
        df, forming = cache_info.get(symbol, (None, None))
        tick = mt5.symbol_info_tick(symbol)
        risk, limit = telemetry.route_risk(symbol, route, df, snap["balance"]) if df is not None else (None, None)
        snap["routes"].append({"symbol": symbol, "tf": route["timeframe"], "setup": route["setup"],
                               "state": states.get(symbol, "…"),
                               "next_close": telemetry.next_close_text(forming, TF_SECS[route["timeframe"]],
                                                                       int(getattr(tick, "time", 0) or 0), now),
                               "risk": risk, "limit": limit,
                               "study": quant_manager.is_study_route(route)})
        snap["positions"] += [p for p in telemetry.bot_positions(symbol) if p["setup"] == route["setup"]]
    return snap


# --- painel --------------------------------------------------------------------
# Cores ANSI de 256 cores (funcionam no console do Windows 10+ apos os.system("")).

def _fg(n):
    return f"\x1b[38;5;{n}m"


def _bg(n):
    return f"\x1b[48;5;{n}m"


RESET, BOLD, DIM = "\x1b[0m", "\x1b[1m", "\x1b[2m"
ORANGE, GREEN, RED, AMBER, BLUE, CYAN, PURPLE, GREY, WHITE = (
    _fg(208), _fg(114), _fg(203), _fg(221), _fg(75), _fg(80), _fg(141), _fg(245), _fg(255))
ROUTE_COLORS = (CYAN, PURPLE, BLUE, AMBER)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _vis(s):
    """Largura visivel (sem codigos ANSI; emojis contam 2)."""
    plain = _ANSI.sub("", s)
    return len(plain) + sum(1 for ch in plain if ord(ch) > 0x2600 and ch not in "✓─…·")


def _pad(s, width):
    return s + " " * max(0, width - _vis(s))


def _money(v):
    if not v:
        return f"{WHITE}$0.00{RESET}"
    return f"{GREEN if v > 0 else RED}{BOLD}{'+' if v > 0 else '-'}${abs(v):.2f}{RESET}"


def _state(text):
    up = text.upper()
    if "POSI" in up or "SAIDA" in up:
        color = GREEN
    elif "ERRO" in up or "SEM TICK" in up or "SEM DADOS" in up or "MAX LOSS" in up:
        color = RED
    elif any(k in up for k in ("AGUARD", "EXPIRADO", "REJEITADO", "MARGEM", "FECHADO")):
        color = AMBER
    else:
        color = BLUE
    return f"{color}{text}{RESET}"


def _section(title):
    return f" {ORANGE}{BOLD}▍{title}{RESET}"


def render_panel(snap, now=None):
    now = now or datetime.now().strftime("%d/%m %H:%M:%S")
    left = "  ◆ MT5BOT  ·  MODO QUANT"
    bar = f"{_bg(208)}{_fg(16)}{BOLD}{left}{' ' * (WIDTH - len(left) - len(now) - 2)}{now}  {RESET}"
    badge = f"{_bg(160)}{WHITE}{BOLD} REAL {RESET}" if snap["real"] else f"{_bg(28)}{WHITE}{BOLD} DEMO {RESET}"
    lbl = lambda s: f"{GREY}{s}{RESET}"
    out = [bar, "",
           f" {badge} {lbl('Conta')} {WHITE}{snap['login']}{RESET}   {lbl('Saldo')} {WHITE}{BOLD}${snap['balance']:.2f}{RESET}"
           f"   {lbl('Patrimônio')} {WHITE}${snap['equity']:.2f}{RESET}   {lbl('Margem livre')} {WHITE}${snap['free']:.2f}{RESET}",
           f"        {lbl('Hoje')} {_money(snap['today'])}   {lbl('Placar quant')} {WHITE}{snap['n_trades']} trades{RESET}"
           f" {GREY}({snap['wins']} no lucro){RESET}  {_money(snap['net'])}", "",
           _section("ROTAS"),
           f"   {GREY}{_pad('ATIVO', 17)}{_pad('ESTADO', 29)}{_pad('PRÓX. CANDLE', 17)}RISCO / LIMITE{RESET}"]
    for i, r in enumerate(snap["routes"]):
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        name = f"{color}{BOLD}{r['symbol']}{RESET} {GREY}{r['tf']} {r['setup']}{RESET}"
        if r.get("study"):
            risk = f"{GREY}📘 estudo (sem dinheiro){RESET}"
        elif r["risk"] is None:
            risk = f"{GREY}—{RESET}"
        elif r["risk"] <= r["limit"]:
            risk = f"{GREEN}✓ ${r['risk']:.2f}{RESET} {GREY}/ ${r['limit']:.2f}{RESET}"
        else:
            risk = f"{AMBER}🔒 ${r['risk']:.2f} > ${r['limit']:.2f}{RESET}"
        closed = "fechado" in r["next_close"]
        nxt = f"{GREY if closed else WHITE}{r['next_close']}{RESET}"
        out.append(f"   {_pad(name, 17)}{_pad(_state(r['state'][:27]), 29)}{_pad(nxt, 17)}{risk}")
    out += ["", _section("POSIÇÕES DO ROBÔ")]
    if not snap["positions"]:
        out.append(f"   {GREY}nenhuma — aguardando sinal{RESET}")
    for p in snap["positions"]:
        side = f"{GREEN}{BOLD}▲ BUY{RESET}" if p["side"] == "BUY" else f"{RED}{BOLD}▼ SELL{RESET}"
        tp = f"  {GREY}TP{RESET} {p['tp']:.2f}" if p["tp"] else ""
        out.append(f"   {WHITE}{BOLD}{p['symbol']}{RESET} {side} {p['volume']} {GREY}@{RESET} {p['open']:.2f}"
                   f"  {GREY}SL{RESET} {p['sl']:.2f}{tp}   {_money(p['profit'])}")
    out += ["", _section("EVENTOS")]
    if not snap["events"]:
        out.append(f"   {GREY}nenhum ainda{RESET}")
    for t, lvl, msg in snap["events"]:
        up = msg.upper()
        color = (RED if lvl >= logging.ERROR else AMBER if lvl >= logging.WARNING
                 else GREEN if ("MERCADO" in up and "ENVIANDO" in up) or "SAIDA" in up or "LIQUIDANDO" in up else WHITE)
        out.append(f"   {GREY}{t}{RESET}  {color}{msg[:62]}{RESET}")
    key = lambda k: f"{_bg(238)}{WHITE}{BOLD} {k} {RESET}"
    # Sem barra invertida dentro de {} da f-string: SyntaxError no Python < 3.12.
    panic_key, log_path = key(".\\bot.bat panic"), "%APPDATA%\\mt5bot\\logs"
    out += ["", f"{GREY}{'─' * WIDTH}{RESET}",
            f" {key('Ctrl+C')} {GREY}parar{RESET}   {panic_key} {GREY}emergência{RESET}   {GREY}log: {log_path}{RESET}"]
    return "\n".join(out)


# --- loop ----------------------------------------------------------------------

def run(once=False, interval=5, plain=False):
    if not terminal.initialize():
        logging.error(f"Falha ao conectar no MT5: {mt5.last_error()}")
        print(f"Falha ao conectar no MT5: {mt5.last_error()}. Abra o terminal e faca login.")
        return 1
    acc = mt5.account_info()
    logging.info(f"Quant runner conectado: conta {acc.login} ({'REAL' if acc.trade_mode == 2 else 'DEMO'}) "
                 f"saldo ${acc.balance:.2f} | rotas: "
                 + ", ".join(f"{s} {r['timeframe']} {r['setup']}" for s, r in config.QUANT_ROUTES.items()))
    if not plain:
        os.system("")  # liga as cores ANSI no console do Windows
        sys.stdout.write("\x1b[?25l")  # esconde o cursor enquanto o painel roda
    cache = CandleCache()
    states, last_logged = {}, {}
    try:
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
    finally:
        if not plain:
            sys.stdout.write("\x1b[?25h")  # devolve o cursor


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
