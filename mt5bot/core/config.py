"""Parametros de configuracao do MT5Bot."""

import logging
import MetaTrader5 as mt5  # type: ignore

# --- Logging ---
LOG_LEVEL = logging.INFO

# --- Simbolos e Timeframe ---
AVAILABLE_SYMBOLS = [
    # B3 Brasil (Indice, Dolar e Acoes)
    "WIN", "WDO", "PETR4", "VALE3", "ITUB4", "BBDC4",
    # Forex Principais
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    # Forex Cruzados
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD",
    # Indices Globais
    "HK50", "HKG50", "US500", "SP500", "NAS100", "USTEC", "US30", "DJ30", "GER40", "DAX40", "UK100", "JPN225",
    # Commodities & Metais
    "XAUUSD", "XAGUSD", "WTI", "USOIL",
    # Criptomoedas
    "BTCUSD", "ETHUSD"
]

SYMBOLS = []  # Preenchido pela TUI no startup
TIMEFRAME = mt5.TIMEFRAME_H1

# Timeframes disponiveis para selecao do usuario
AVAILABLE_TIMEFRAMES = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}

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
    "M1":  0.5,
    "M5":  0.7,
    "M15": 1.0,
    "M30": 1.0,
    "H1":  1.5,
    "H4":  2.0,
    "D1":  3.0,
}

# --- Alvo Adaptativo & ATR ---
ADAPTIVE_TARGET_ENABLED = True
ADAPTIVE_TARGET_LOOKBACK = 20
ATR_PERIOD = 14
ATR_AVG_PERIOD = 50
ATR_HIGH_VOL_THRESHOLD = 1.5
ATR_DAMPING_FACTOR = 0.8
TICK_OFFSET = 1
MAGIC = 20260731
SCAN_INTERVAL_SECONDS = 5
RETRY_INTERVAL_SECONDS = 5
RATES_COUNT = 300

# --- Filtro de Volume Relativo (RVOL) ---
RVOL_FILTER_ENABLED = True
RVOL_LOOKBACK = 20
RVOL_THRESHOLD = 1.15

# --- Filtros do Maestro Fase 2 ---
CONFIG_SETUPS = {
    "9.1": True,
    "9.2": True,
    "9.3": True,
    "9.4": True,
    "PC": True,
    "FFFD": True,
    "GAP": True,
    "DiNapoli": True,
    "IFR2": True,
    "SAR": True,
    "RompFalso": True
}
MIN_RISK_REWARD = 1.0
SCORE_WEIGHTS = {
    "rrr": 30.0,
    "congruencia_macro": 25.0,
    "proximidade_media": 20.0,
    "volume": 25.0,
    "ifr9": 10.0,
    "vwap": 10.0,
}

# --- Filtros macro Fase 2.5 ---
MM50_ENABLED = True
IFR9_ENABLED = True
VWAP_ENABLED = True
VWAP_MAX_DEVIATION_ATR = 2.0

# --- Setup 9.2 ---
SETUP_92_ENABLED = True
SETUP_92_MAX_CANDLES_WATCHING = 10
SETUP_92_EMA_AGAINST_LIMIT = 2

# --- Persistencia & Contas ---
STATE_FILE = "state.json"
DEFAULT_ACCOUNT_BALANCE = 10000.0


# --- Shutdown Default Action ---
SHUTDOWN_DEFAULT_ACTION = "cancel-open"
SHUTDOWN_WAIT_SECONDS = 600


# --- Modulo de Protecao de Capital (Fase 1 - Opcao A) ---
MAX_RISK_PER_TRADE_PERCENT = 1.0
ABSOLUTE_MAX_TRADE_RISK_PERCENT = 1.5
MAX_DAILY_LOSS_PERCENT = 2.0
MAX_SPREAD_POINTS = 50
ENABLE_BREAKEVEN = True
BREAKEVEN_ATR_RATIO = 1.0
MIN_STOP_SPREAD_MULTIPLIER = 1.5

# --- Trailing Stop dinamico (spec 5.7) ---
# Apos o breakeven, o SL acompanha o mercado barra a barra.
# Modos: "candle" (extremidade do penultimo candle) | "ema9" | "mm21".
# Se o preco perder a media de referencia do modo, o restante e liquidado.
TRAILING_ENABLED = True
TRAILING_MODE = "mm21"

# --- Posicoes externas (entradas manuais do usuario no MT5) ---
# Se True, o bot adota posicoes abertas manualmente no mesmo simbolo,
# registra no tracker (setup "MANUAL") e passa a guiar alvo/stop.
MANAGE_EXTERNAL_POSITIONS = True
EXTERNAL_POSITION_SETUP_NAME = "MANUAL"

# --- Horarios de Negociacao ---
TRADING_HOURS_ENABLED = True
TRADING_START_TIME = "09:15"
TRADING_END_TIME = "16:45"
FORCE_CLOSE_TIME = "17:30"

# Horarios de negociacao especificos por ativo no fuso horario local (Horario de Brasilia BRT)
SYMBOL_TRADING_HOURS = {
    # B3 Brasil (Mini Indice, Mini Dolar e Acoes)
    "WIN":   {"start": "09:15", "end": "17:15", "force_close": "17:30"},
    "WDO":   {"start": "09:15", "end": "17:15", "force_close": "17:30"},
    "PETR4": {"start": "10:00", "end": "17:15", "force_close": "17:30"},
    "VALE3": {"start": "10:00", "end": "17:15", "force_close": "17:30"},
    "ITUB4": {"start": "10:00", "end": "17:15", "force_close": "17:30"},
    "BBDC4": {"start": "10:00", "end": "17:15", "force_close": "17:30"},

    # Bolsa de Hong Kong (HK50 / Hang Seng) — Abre as 22:15 BRT
    "HK50":  {"start": "22:15", "end": "12:00", "force_close": "12:30"},
    "HKG50": {"start": "22:15", "end": "12:00", "force_close": "12:30"},

    # Japao Nikkei 225
    "JPN225":{"start": "21:00", "end": "15:00", "force_close": "15:30"},

    # Indices Americanos (S&P500, Nasdaq, Dow Jones)
    "US500": {"start": "10:30", "end": "17:00", "force_close": "17:30"},
    "SP500": {"start": "10:30", "end": "17:00", "force_close": "17:30"},
    "NAS100":{"start": "10:30", "end": "17:00", "force_close": "17:30"},
    "USTEC": {"start": "10:30", "end": "17:00", "force_close": "17:30"},
    "US30":  {"start": "10:30", "end": "17:00", "force_close": "17:30"},
    "DJ30":  {"start": "10:30", "end": "17:00", "force_close": "17:30"},

    # Indices Europeus (Alemanha DAX / Reino Unido UK100)
    "GER40": {"start": "04:00", "end": "17:00", "force_close": "17:30"},
    "DAX40": {"start": "04:00", "end": "17:00", "force_close": "17:30"},
    "UK100": {"start": "04:00", "end": "17:00", "force_close": "17:30"},

    # Forex Principal e Cruzados (Londres e Nova York)
    "EURUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "GBPUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "USDJPY":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "AUDUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "USDCAD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "USDCHF":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "NZDUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "EURGBP":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "EURJPY":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "GBPJPY":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "AUDJPY":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "EURAUD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},

    # Commodities (Ouro, Prata, Petroleo)
    "XAUUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "XAGUSD":{"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "WTI":   {"start": "03:00", "end": "18:00", "force_close": "18:30"},
    "USOIL": {"start": "03:00", "end": "18:00", "force_close": "18:30"},

    # Criptomoedas (24/7)
    "BTCUSD":{"start": "00:00", "end": "23:59", "force_close": "23:59"},
    "ETHUSD":{"start": "00:00", "end": "23:59", "force_close": "23:59"},
}

# --- Filtro Multi-Timeframe (MTF) ---
MTF_FILTER_ENABLED = True
MTF_TIMEFRAME_MAP = {
    "M1":  "M5",
    "M5":  "M30",
    "M15": "H1",
    "M30": "H4",
    "H1":  "D1",
    "H4":  "D1",
    "D1":  "D1",
}

# --- Setup 9.3 (Larry Williams) ---
SETUP_93_ENABLED = True
SETUP_93_MAX_PULLBACK_CANDLES = 2

# --- Filtro de Volume Relativo (RVOL) ---
RVOL_FILTER_ENABLED = True
RVOL_LOOKBACK = 20
RVOL_THRESHOLD = 1.15
