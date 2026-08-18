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
    "XAUUSD", "XAGUSD", "WTI", "USOIL"
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

# --- Roteamento por Ativo (Fase 3: Maestro Multi-Estrategia) ---
ASSET_SETUPS = {
    "default": ["9.1", "9.2", "9.3", "9.4", "PC", "FFFD", "GAP", "DiNapoli", "IFR2", "SAR", "RompFalso"],
    "HK50": ["russian_bb"],
    "HKG50": ["russian_bb"],
    # EURUSD: setups 9.x PERDEM (PF 0.45, backtest 12/2025-08/2026). russian_bb
    # e lucrativo mas so opera com saldo >= ~$60. Como temos pouco saldo, vamos
    # ligar o 'judas' (Setup probabilistico de horario). O motor ja o mantem na garagem
    # esperando a margem chegar a $100 por seguranca.
    "EURUSD": ["judas"],
    # Motor Otimizado JP225: Ponto Contínuo (PC) na Sessão Asiática
    "JP225": ["PC"],
    "JPN225": ["PC"],
}

ASSET_MIN_LOTS = {
    "HK50": 0.01,
    "HKG50": 0.01,
    "JP225": 0.01,
    "JPN225": 0.01,
}

# --- Bloqueio de Garagem (Capital Mínimo) ---
# Impede o bot de ligar motores pesados em contas pequenas.
MIN_BALANCE_REQUIREMENTS = {
    "JP225": 300.00,
    "JPN225": 300.00,
    "EURUSD": 100.00,
}

# --- Setup Judas (Fading the Open) — EURUSD ---
JUDAS_TARGET_TIMES = ["04:15", "11:15"] # Horarios dos fechamentos dos candles a serem operados
JUDAS_SL_POINTS = 150.0  # SL (15 pips para absorver spread)
JUDAS_TP_POINTS = 300.0  # TP (30 pips)
POINT_OVERRIDE = 0.00001 # Point padrao do EURUSD

# --- Setup Russo (BB + RSI Mean Reversion) — HK50 ---
# Parametros validados por otimizacao convexa (60k candles M5, spread 4.5,
# 07/2025-08/2026). Config MELHOR: RSI 30/75, min_bw 50, SMA200, janela
# institucional 22:15-01:00 BRT, saida no fim da sessao.
# Resultado: PF 1.93, DD 9.6%, +25% do capital em 15 meses (~1.5%/mes).
#
# v2.4.1 (grid + walk-forward 13 meses): min_bw 40, RSI overbought 70.
#   Treino escolheu min_bw=40 RSI=30/70 SMA200=True (PF 2.61 no treino);
#   out-of-sample +$1.06 vs +$0.37 do baseline. Em 13 meses completos:
#   19 ops, PF 2.27, DD 2.7%, WR 52.6%, lucro +$1.93 vs +$1.22 (+58%).
#   Melhora lucro E reduz risco (menor drawdown) — nao e overfit.
RUSSIAN_BB_MIN_WIDTH = 40.0          # largura minima da banda (unidade de preco)
RUSSIAN_BB_RSI_OVERSOLD = 30.0       # compra quando IFR14 < 30
RUSSIAN_BB_RSI_OVERBOUGHT = 70.0     # venda quando IFR14 > 70

# --- Override por ativo (Fase 3: Maestro Multi-Estrategia) ---
# Cada ativo pode ter parametros proprios do russian_bb. Se o ativo nao estiver
# aqui, usa os valores globais acima (RUSSIAN_BB_MIN_WIDTH/RSI_*).
# EURUSD: otimizado por grid + walk-forward COM filtro SMA200 (50k candles M5,
# spread 9 ticks, 12/2025-08/2026). Treino PF 1.28 / teste PF 1.85 (nao overfit),
# 60 ops PF 1.42 +$15.33 intacto. Combos 9.x PERDEM no EURUSD (PF 0.45).
# ATENCAO: russian_bb no EURUSD so opera com saldo >= ~$60 (SL = meia banda
# ~$0.59 = 3.6% do saldo a $16.47 -> Risk Shield rejeita tudo abaixo disso).
RUSSIAN_BB_PARAMS = {
    "HK50":  {"min_width": 40.0,   "rsi_oversold": 30.0, "rsi_overbought": 70.0},
    "HKG50": {"min_width": 40.0,   "rsi_oversold": 30.0, "rsi_overbought": 70.0},
    "EURUSD": {"min_width": 0.0008, "rsi_oversold": 35.0, "rsi_overbought": 75.0},
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
# Fechar a posicao aberta quando a perda diaria (realizada + flutuante) bater
# o limite. A protecao base so bloqueava novas entradas; esta opcao liquida a
# posicao atual a mercado para conter o risco real (protecao de capital).
DAILY_MAX_LOSS_CLOSE_ENABLED = True
MAX_SPREAD_POINTS = 50
# Limite de spread por simbolo (pontos). HK50 tem spread tipico de ~450 pts
# em baixa liquidez; o limite global de 50 pontos bloquearia toda operacao.
SYMBOL_MAX_SPREAD_POINTS = {
    "HK50": 500,
    "HKG50": 500,
}
ENABLE_BREAKEVEN = True
BREAKEVEN_ATR_RATIO = 1.0
MIN_STOP_SPREAD_MULTIPLIER = 1.5

# --- Trailing Stop dinamico (spec 5.7) ---
# Tipos disponiveis: "candle", "ema9", "mm21", "atr"
# "atr" comprovado por backtest de 2 anos (HK50) como mais lucrativo.
TRAILING_ENABLED = True
TRAILING_MODE = "atr"

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
    "HK50":  {"start": "22:15", "end": "01:00", "force_close": "01:30"},
    "HKG50": {"start": "22:15", "end": "01:00", "force_close": "01:30"},

    # Japao Nikkei 225 (Janela Asiática Otimizada - Setup PC)
    "JP225": {"start": "21:00", "end": "06:00", "force_close": "06:30"},
    "JPN225":{"start": "21:00", "end": "06:00", "force_close": "06:30"},

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
    # EURUSD (russian_bb): JANELA LUCRATIVA validada em 94 trades (M5,
    # spread 9t, lote dinamico). Sessao Londres 03:00-09:00 BRT concentra
    # 30 ops e +$13.00 de +$7.75 total — sinais fora dela DESTROEM o lucro
    # (especialmente fechamento 21:00-23:59 BRT, -$3.75). Fora dessa janela
    # o bot ignora o setup e avisa o usuario.
    "EURUSD":{"start": "03:00", "end": "09:00", "force_close": "09:30"},
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

