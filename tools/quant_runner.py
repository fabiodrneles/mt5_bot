"""Executor headless das rotas quant (config.QUANT_ROUTES).

Uso:
    python tools\\quant_runner.py            # roda continuamente (Ctrl+C para parar)
    python tools\\quant_runner.py --once     # um ciclo por rota e sai (diagnostico)

Faz o mesmo que o Maestro faria com `/add HK50 H4` e `/add US500 D1`: puxa as
velas FECHADAS do MT5 e chama execution_manager.manage_cycle, que despacha para
o caminho quant. Loga so mudancas de estado para nao encher o disco.
"""
import argparse
import logging
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import MetaTrader5 as mt5
import pandas as pd

from mt5bot.core import config
from mt5bot.execution import execution_manager

TF_MAP = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}


def _setup_logging():
    # Console do Windows (cp1252) nao imprime os emojis de estado.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(os.path.join(_ROOT, "logs", "quant_runner.log"), encoding="utf-8")],
    )


def _closed_candles(symbol, timeframe):
    rates = mt5.copy_rates_from_pos(symbol, TF_MAP[timeframe], 1, 400)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def run(once=False, interval=5):
    if not mt5.initialize():
        logging.error(f"Falha ao conectar no MT5: {mt5.last_error()}")
        return 1
    acc = mt5.account_info()
    logging.info(f"Quant runner conectado: conta {acc.login} ({'REAL' if acc.trade_mode == 2 else 'DEMO'}) "
                 f"saldo ${acc.balance:.2f} | rotas: "
                 + ", ".join(f"{s} {r['timeframe']} {r['setup']}" for s, r in config.QUANT_ROUTES.items()))
    last_state = {}
    while True:
        for symbol, route in config.QUANT_ROUTES.items():
            try:
                mt5.symbol_select(symbol, True)
                df = _closed_candles(symbol, route["timeframe"])
                state = "🔴 SEM DADOS" if df is None else execution_manager.manage_cycle(
                    symbol, df, timeframe_name=route["timeframe"])
            except Exception as e:
                logging.exception(f"[{symbol}] Erro no ciclo quant: {e}")
                state = "🔴 ERRO"
            if once or last_state.get(symbol) != state:
                logging.info(f"[{symbol} {route['timeframe']}] {state}")
                last_state[symbol] = state
        if once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=5)
    args = ap.parse_args()
    _setup_logging()
    try:
        sys.exit(run(once=args.once, interval=args.interval))
    except KeyboardInterrupt:
        logging.info("Quant runner encerrado pelo usuario.")
