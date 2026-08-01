"""Parametros de configuracao do MT5Bot."""

import MetaTrader5 as mt5

# --- Simbolos e Timeframe ---
AVAILABLE_SYMBOLS = ["HK50", "EURUSD", "US500"]
SYMBOLS = []  # Preenchido pela TUI no startup
TIMEFRAME = mt5.TIMEFRAME_H1

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