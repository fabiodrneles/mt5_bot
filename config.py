"""Parametros de configuracao do MT5Bot."""

import logging
import MetaTrader5 as mt5

# --- Logging ---
LOG_LEVEL = logging.INFO

# --- Simbolos e Timeframe ---
AVAILABLE_SYMBOLS = ["HK50", "EURUSD", "US500"]
SYMBOLS = []  # Preenchido pela TUI no startup
TIMEFRAME = mt5.TIMEFRAME_H1

# Timeframes disponiveis para selecao do usuario
# Mapeia nome amigavel -> constante do MT5
AVAILABLE_TIMEFRAMES = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}

# Nome do timeframe atualmente selecionado (para exibicao)
TIMEFRAME_NAME = "H1"

# --- EMAs ---
EMA_PERIOD = 9
EMA_FILTER_PERIOD = 21

# --- Volume ---
VOLUME_INITIAL = 0.01

# --- Saida Parcial ---
PARTIAL_EXIT_ENABLED = True
PARTIAL_EXIT_PERCENT = 0.50
PARTIAL_EXIT_TARGET = 1.00

# --- Filtro Flat ---
FLAT_FILTER_ENABLED = True
FLAT_THRESHOLD_TICKS = 5
FLAT_THRESHOLD_MULTIPLIERS = {
    "M1":  0.5,   # 5 * 0.5 = 2.5 ticks (mais sensivel)
    "M5":  0.7,   # 5 * 0.7 = 3.5 ticks
    "M15": 1.0,   # 5 * 1.0 = 5 ticks (padrao atual)
    "M30": 1.0,   # 5 * 1.0 = 5 ticks
    "H1":  1.5,   # 5 * 1.5 = 7.5 ticks (menos sensivel)
    "H4":  2.0,   # 5 * 2.0 = 10 ticks
    "D1":  3.0,   # 5 * 3.0 = 15 ticks
}

# --- Offsets ---
TICK_OFFSET = 1

# --- Intervalos ---
SCAN_INTERVAL_SECONDS = 10
RETRY_INTERVAL_SECONDS = 30

# --- Dados ---
RATES_COUNT = 100

# --- Identificacao ---
MAGIC = 20260731

# --- Alvo Adaptativo ---
ADAPTIVE_TARGET_ENABLED = True
ADAPTIVE_TARGET_LOOKBACK = 20  # Candles para calcular amplitude mediana

# --- ATR Dinamico ---
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
ATR_HIGH_VOL_THRESHOLD = 1.5
ATR_DAMPING_FACTOR = 0.8

# --- Setup 9.2 ---
SETUP_92_ENABLED = True
SETUP_92_MAX_CANDLES_WATCHING = 10
SETUP_92_EMA_AGAINST_LIMIT = 2

# --- Persistencia ---
STATE_FILE = "state.json"
 
# --- Shutdown behavior ---
# Default action on interactive shutdown: 'save-only' | 'wait-flat' | 'cancel-open'
SHUTDOWN_DEFAULT_ACTION = 'save-only'
# Maximum seconds to wait when using 'wait-flat' before forcing save and exit
SHUTDOWN_WAIT_SECONDS = 600