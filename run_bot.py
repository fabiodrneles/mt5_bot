"""Script de arranque direto — sem TUI, conecta e opera."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import MetaTrader5 as mt5
import config
import logger
import strategy
import time
import signal as sig
from datetime import datetime
import pytz

# Conectar MT5
ok = mt5.initialize()
if not ok:
    print("Falha ao conectar MT5:", mt5.last_error())
    sys.exit(1)

account = mt5.account_info()
print(f"Conectado: {account.login} ({account.name}) | Balance: {account.balance} {account.currency}")

# Configurar ativos
config.SYMBOLS = ["HK50"]
for s in config.SYMBOLS:
    mt5.symbol_select(s, True)

s92 = "Ativado" if config.SETUP_92_ENABLED else "Desativado"
print(f"Ativos: {config.SYMBOLS}")
print(f"Volume: {config.VOLUME_INITIAL} | Timeframe: H1")
print(f"Setup 9.1: Ativado | Setup 9.2: {s92}")
print()

# Inicializar estados
if not strategy.initialize_symbol_states():
    print("Falha ao inicializar estados. Encerrando.")
    mt5.shutdown()
    sys.exit(1)

timezone = pytz.timezone("Etc/UTC")
last_candle_time = {s: None for s in config.SYMBOLS}
shutdown = False


def handler(signum, frame):
    global shutdown
    shutdown = True
    print("\nShutdown solicitado...")


sig.signal(sig.SIGINT, handler)

print("Bot ativo. Monitorando candles H1... (Ctrl+C para parar)")
print("=" * 60)

while not shutdown:
    try:
        for symbol in list(config.SYMBOLS):
            if shutdown:
                break

            sym_info = mt5.symbol_info(symbol)
            if sym_info and sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                continue

            rates = mt5.copy_rates_from_pos(symbol, config.TIMEFRAME, 0, config.RATES_COUNT)
            if rates is None or len(rates) < config.RATES_COUNT:
                count = len(rates) if rates is not None else 0
                print(f"[{symbol}] Dados insuficientes ({count} rates)")
                continue

            current_closed_candle = rates[-2]
            candle_dt = datetime.fromtimestamp(current_closed_candle[0], timezone)

            if last_candle_time[symbol] is None or candle_dt > last_candle_time[symbol]:
                print(f"[{symbol}] Novo candle H1: {candle_dt}")
                last_candle_time[symbol] = candle_dt
                strategy.evaluate(symbol, current_closed_candle, rates)
                state = strategy.symbol_states[symbol].state.name
                print(f"[{symbol}] Estado atual: {state}")

        if not shutdown:
            time.sleep(config.SCAN_INTERVAL_SECONDS)

    except Exception as e:
        print(f"Erro no loop: {e}")
        time.sleep(config.RETRY_INTERVAL_SECONDS)

# Graceful shutdown
print("Executando shutdown...")
for symbol in config.SYMBOLS:
    orders = mt5.orders_get(symbol=symbol)
    if orders:
        for o in orders:
            if o.magic == config.MAGIC:
                print(f"[{symbol}] Cancelando ordem pendente {o.ticket}")
                mt5.order_remove(o.ticket)

mt5.shutdown()
print("Bot encerrado.")
