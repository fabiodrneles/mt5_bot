<div align="center">
  <img src="docs/assets/banner.jpg" alt="MT5Bot Maestro" width="100%">
</div>

<div align="center">

**🌍 Language:** [Português](README.md) | **English**

# MT5Bot Maestro

**Algorithmic trading bot for MetaTrader 5 in Python and Go, built for small accounts.**
Strict risk management, out-of-sample validated strategies, and respect for your margin.

![Version](https://img.shields.io/badge/version-2.12.0-FF7300?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Go](https://img.shields.io/badge/Go-Maestro-00ADD8?style=flat-square&logo=go&logoColor=white)
![MetaTrader 5](https://img.shields.io/badge/MetaTrader-5-1F6FEB?style=flat-square)
![Tests](https://img.shields.io/badge/tests-184%20passing-2EA043?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-555?style=flat-square)

</div>

> [!WARNING]
> **Trading carries a real risk of loss.** Backtest results do not guarantee future results. Test on a **demo account** first. On a live account, only use money you can afford to lose. This software is not investment advice.

---

## 📑 Contents

1. [What it is](#-what-it-is)
2. [Requirements](#-requirements)
3. [Installation](#-installation)
4. [Getting started: pick a mode](#-getting-started-pick-a-mode)
5. [Quant Mode (recommended)](#-quant-mode-recommended)
6. [Maestro Mode (interactive)](#-maestro-mode-interactive)
7. [Strategies](#-strategies)
8. [Capital protection](#️-capital-protection)
9. [`bot.bat` commands](#-botbat-commands)
10. [Configuration](#️-configuration)
11. [Data and logs](#-data-and-logs)
12. [Emergency: how to stop everything](#-emergency-how-to-stop-everything)
13. [Backtesting and strategy research](#-backtesting-and-strategy-research)
14. [Machine Learning (XGBoost)](#-machine-learning-xgboost)
15. [Telegram notifications](#-telegram-notifications)
16. [Architecture](#️-architecture)
17. [Troubleshooting](#-troubleshooting)
18. [Development](#-development)

---

## 💡 What it is

MT5Bot connects to the **MetaTrader 5** terminal running on your Windows machine and trades on its own. It reads closed candles, looks for signals, sizes the position, and sends orders with a stop loss.

The project has two operating modes:

| Mode | For whom | What runs |
|---|---|---|
| **Quant** (`bot.bat quant`) | Small accounts that want **only what has been validated** | 2 strategies tested with real costs and out of sample |
| **Maestro** (`mt5bot.bat`) | Users who want to explore the 9.x family, Ponto Contínuo, the Russian Setup and others | Interactive panel with several bots in parallel |

---

## 🧰 Requirements

- **Windows 10/11.** The `MetaTrader5` Python library only exists for Windows.
- **MetaTrader 5** installed, logged in to your broker, and **open** while the bot runs.
- **Python 3.10+** (tested on 3.13).
- **Go 1.21+**: to build the Maestro the first time (`mt5bot.bat` does it by itself, or run `bot.bat build`). Prebuilt binaries are on the [Releases](https://github.com/fabiodrneles/mt5_bot/releases) page.
- Modest hardware is fine: the project runs on a 4th-gen i3 with 4 GB of RAM.

---

## 📦 Installation

```powershell
# 1. Get the project
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# 2. Install dependencies (MetaTrader5, pandas, numpy, pytz, xgboost, pytest)
pip install -e ".[dev]"
pip install -r requirements-ml.txt   # scikit-learn, used to train XGBoost
pip install psutil                   # optional: only for "bot.bat hardware"
```

**Set up MetaTrader 5:**

1. Log in to your account (demo or live).
2. Turn on the **Algo Trading** button in the toolbar. It must be green.
3. In *Tools → Options → Expert Advisors*, check **Allow algorithmic trading**.
4. In *Market Watch*, keep the symbols you will trade visible (e.g. `HK50`, `US500`).

**Check the connection:**

```powershell
.\bot.bat diagnose
```

```
MT5: Conectado | Saldo: $16.26 | Margem Livre: $14.35
Erros nas ultimas 24h (bot.log): 0
```

> Run every command **from the project root**. In PowerShell, use the `.\` prefix (e.g. `.\bot.bat diagnose`); in `cmd`, `bot.bat diagnose` is enough. The bot's console output is in Portuguese.

---

## 🚀 Getting started: pick a mode

```
               Small account or first time?
                            │
            ┌──────── yes ──┴── no ────────┐
            ▼                              ▼
     bot.bat quant                    mt5bot.bat
 (validated strategies only)   (Maestro panel: /study, /add)
```

If you have never run the bot, start with **Quant Mode on a demo account** and let it run for a few weeks before moving to a live account.

---

## 📈 Quant Mode (recommended)

```powershell
.\bot.bat quant
```

It runs continuously, with one cycle every 5 seconds, and shows a **live panel** (labels are in Portuguese). Keep the window open and stop it with **Ctrl+C**:

```
  ◆ MT5BOT  ·  MODO QUANT                                       26/10 22:20:00
 REAL  Conta 50352457   Saldo $16.26   Patrimônio $16.38   Margem livre $14.20
        Hoje +$0.12   Placar quant 3 trades (2 no lucro)  +$0.35

 ▍ROTAS
   ATIVO            ESTADO                       PRÓX. CANDLE     RISCO / LIMITE
   HK50 H4 PULLB    🟢 EM POSIÇÃO (PULLB BUY)     em 1h 05m        ✓ $0.21 / $0.33
   US500 D1 RSI2MR  ⏳ AGUARDANDO MERCADO         mercado fechado  ✓ $1.62 / $1.95

 ▍POSIÇÕES DO ROBÔ
   HK50 ▲ BUY 0.01 @ 23050.00  SL 22850.00  TP 23450.00   +$0.12

 ▍EVENTOS
   26/10 22:15  [HK50] PULLB BUY @ 23050.0 SL=22850.00 TP=23450.0 lote=0.01
────────────────────────────────────────────────────────────────────────────────
  Ctrl+C  parar    .\bot.bat panic  emergência   log: %APPDATA%\mt5bot\logs
```

- **Risk / limit (RISCO / LIMITE):** ✓ when the trade fits the limit; 🔒 when it is locked to protect margin, showing why.
- **Next candle (PRÓX. CANDLE):** time left until the candle closes, by the server clock. Shows "mercado fechado" (market closed) on weekends.
- **Quant scoreboard (Placar quant):** only quant-route trades, with real profit (commission and swap included).
- `python tools\quant_runner.py --plain` prints log lines only, without the panel (useful for redirecting to a file). `--once` runs one cycle and exits.
- The panel is lightweight: the 400 candles are only downloaded when a candle closes.

### Quant Mode strategies

Both came out of a search over **3,150 combinations** (15 symbols × 4 timeframes × 4 strategy families). The search used the **real spread of each candle**, the broker's commission and swap. Parameters were chosen using only the first 60% of history, and the results below come from the last 40%, which the optimizer never saw.

| Route | Rule | History (0.01 lot) | Risk per trade |
|---|---|---|---|
| **HK50 H4 — PULLB** | Uptrend (EMA20 > EMA50 and price above SMA200). The candle pulls back to the EMA20 and closes above it, and the bot buys. Sells are mirrored. **SL 1 ATR, TP 2 ATR.** | 277 trades over 4.8 years · profit factor 1.24 · **+$9.96** · max drawdown $4.30 | ~$0.21 |
| **US500 D1 — RSI2MR** | RSI(2) < 5 with price above SMA200: buys the sharp dip (sells mirrored). **SL 2 ATR.** Exits when the close crosses the SMA5 or after 15 days. | 54 trades over 9.5 years · profit factor 2.40 · **+$13.19** · max drawdown $3.04 | ~$1.63 |

**How it trades:**
- Entry is **at market, right after the signal candle closes**, just like in the backtest. If more than 10% of the candle's duration has passed, the signal is dropped.
- It always uses the **minimum lot**, with **SL and TP stored in MT5**: the protection holds even if the PC shuts down.
- It does not use scoring, XGBoost, trailing or breakeven, because none of that was part of the validation.

**How much to trust each route** (luck tests in `tools/quant_research/robustness.py`):

| | HK50 H4 PULLB | US500 D1 RSI2MR |
|---|---|---|
| t-statistic (≥ 2 is strong) | 1.65: weak | **2.57: good** |
| Does the same rule work on other indices? | No (8 of 9 lose) | **Yes** (6 of 8 profit) |
| Against 300 random-entry portfolios on HK50 | Beats all 300 | — |

US500 has the strongest evidence: it is Connors' RSI2 effect, documented for decades. HK50 has a signal that adds value *on HK50*, but treat it as a live experiment.

**Want to unlock US500 with a small balance?** Give the route its own limit in `config.py`, e.g. `"US500": {..., "max_risk_pct": 12.0}`. With $16 each stop costs ~$1.63 (10% of the account). The worst historical drawdown was $3.04, with about 6 trades a year. In this installation US500 ships **unlocked at 12%**. To lock it again, remove `"max_risk_pct"` from the route.

**Honest expectations:** this is **cents per trade**. On HK50 the historical average is +$0.036 per trade, about 13% a year on $16, with drawdowns of up to ~$4 along the way. There were losing years (2024: −$1.48). Only dozens of live trades will tell whether it holds up.

### Quant Mode margin safeguards

| Safeguard | Rule | Effect with a $16 balance |
|---|---|---|
| Risk per trade | Loss at SL ≤ **2% of balance** (`QUANT_MAX_RISK_PCT`) | HK50 trades within 2%. **US500 uses its own 12% limit** (`max_risk_pct`); without it, it would only unlock above ~$80. |
| Margin reserve | Free margin left must be ≥ **3× the position's margin** (`QUANT_MARGIN_RESERVE_MULT`) | Never uses all the margin, so there is room for the next attempts |
| Daily loss | Blocks new entries after losing 2% in a day | Caps a bad streak |
| One entry per candle | Never re-enters the same signal | Avoids repeating a loss |

> **Manual positions are respected.** On a *hedging* account, Quant Mode only manages positions it opened itself (bot MAGIC + comment `Q PULLB` / `Q RSI2MR`). A trade you opened by hand on the same symbol is **never touched**.

---

## 🎛 Maestro Mode (interactive)

```powershell
.\mt5bot.bat        # builds the Maestro the first time, then just opens it
# or: .\run.bat     # builds and runs via "go run" (requires Go)
```

The panel opens in the terminal. Each symbol becomes a "bot" (a Python worker) supervised by the Maestro (labels in the screenshot are Portuguese; type `/idioma en` to switch the help and messages):

```
 ◆ MT5BOT MAESTRO v2.12.0   LIVE   MT5 ON   CONTA REAL  ─────────────────── 26/10 22:20:00
 Saldo $16.26   Patrimônio $16.38   Margem livre $14.20   Flutuante +$0.12   Posições do robô 1
╭──────────────────────────────────────╮╭──────────────────────────────────────────────────╮
│ROBÔS  2 ativo(s)                     ││EVENT LOG (Live)                                  │
│● HK50 H4                 [POS] 2h13m ││[HK50|H4] PULLB BUY @ 23050.0 ... Enviando a      │
│  EM POSIÇÃO (PULLB BUY)              ││mercado.                                          │
│  ★ QUANT PULLB · candle em 1h 05m    ││                                                  │
│  ✓ risco $0.21 / limite $0.33        │╰──────────────────────────────────────────────────╯
│  ▲ BUY 0.01 @ 23050.00  +$0.12       │╭──────────────────────────────────────────────────╮
│┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  ││PERFORMANCE RESUMO (Por Ativo)                    │
│● US500 D1               [WAIT] 2h13m ││[HK50|H4] LOTE 0.01  +$0.35  WR 66.7%  3T         │
│  AGUARDANDO MERCADO                  ││[US500|D1] LOTE 0.01  sem dados                   │
╰──────────────────────────────────────╯╰──────────────────────────────────────────────────╯
 | mt5bot ❯ /add US500 D1
```

- **Header:** mode (LIVE/SIMULATOR), MT5 connection, **REAL/DEMO** account, balance, equity, free margin and the bot's floating P/L.
- **One card per bot:** colored state, quant route (★), time until the candle closes, risk × limit (✓ or 🔒) and the open position with P/L.
- **Prompt:** type `/` and suggestions appear in grey; **Tab** completes, **Esc** clears the line and **Ctrl+C** exits.

| Command | What it does |
|---|---|
| `/study HK50 H1` | **Simulation.** Shows signals and opens virtual trades, **no real orders**. Start here. |
| `/add HK50 H4` | Starts the **live** bot on that symbol and timeframe. `HK50 H4` and `US500 D1` use Quant Mode automatically. |
| `/stop HK50` | Stops the bot for that symbol |
| `/list` | Lists running bots |
| `/report` | Dollar report of real trades, by strategy |
| `/dashboard` | Opens the live web dashboard in the browser |
| `/fix` | Restarts bots stuck in a crash loop |
| `/idioma pt\|en\|es` | Changes the interface language |
| `/quit` | Shuts down and keeps orders in MT5 |
| `/quit cancel-open` | Cancels the **bot's** pending orders and shuts down |
| `/quit wait-flat` | Blocks new entries and waits for the **bot's** positions to close |
| `/quit close-all` | **[PANIC]** Closes the **bot's** positions at market (manual ones are kept) |

> ⚠️ **Do not run Quant Mode and `/add` on the same symbol at the same time.** Two processes would fight over the same position.

---

## 🖥 Web dashboard

```powershell
.\bot.bat dashboard     # or /dashboard in the Maestro
```

Opens a **live** panel in the browser (refreshes every 5 s), in Portuguese, English or Spanish:

- **Indicators:** balance, equity, free margin, today's result and the bot's floating P/L, with the REAL/DEMO badge.
- **Quant routes:** risk per trade × limit and time until the next candle.
- **Bot positions** with SL, TP and P/L.
- **Equity curve**, performance (trades, win rate, profit factor, max drawdown) and result per strategy — all in **dollars**, using MT5's real profit.
- **Configuration** (read-only): quant routes, risk locks and setups per symbol.

It runs on Python's standard library only, on `localhost`. Nothing leaves your computer.

---

## 🧠 Strategies

### Validated (Quant Mode)
See the [table above](#quant-mode-strategies). Full details in `memoria/wiki/arquitetura/pesquisa-estrategias-lucrativas.md` (Portuguese).

### Classic (Maestro Mode)
Based on the 9.x setup family (Larry Williams) and Brazilian trading-strategy books. Which setup runs on which symbol is set in `ASSET_SETUPS` (`mt5bot/core/config.py`).

| Setup | Idea | Exit |
|---|---|---|
| **9.1** | EMA9 turns in favor | EMA9 turning against / trailing |
| **9.2** | Shallow pullback against EMA9 in a trend | same |
| **9.3** | Deep pullback with 2 closes | same |
| **9.4** | False pullback (EMA9 turns and turns back) | same |
| **PC** | Ponto Contínuo: touch of the 21 MA in a trend | same |
| **FFFD** | Bollinger: closed outside, closed inside | trailing |
| **GAP** | Opening gap fill > 0.5% | own target (TP) |
| **russian_bb** | Russian Setup: Bollinger + RSI14 (mean reversion) | TP/SL only |
| **judas** | Fading the open (EURUSD, fixed times) | TP/SL only |
| **DiNapoli / IFR2 / SAR / RompFalso** | Auxiliary setups | trailing |

Classic setups go through extra filters before an order: SMA200, multi-timeframe, relative volume (RVOL), scoring (RRR ≥ 1) and the XGBoost veto.

> In a recent backtest the Russian Setup on HK50 was **roughly break-even** (+$0.13 over 7 months, −$0.30 in the last 2). That is why Quant Mode is recommended for small accounts.

---

## 🛡️ Capital protection

| Protection | Setting | Applies to |
|---|---|---|
| 1% of balance risk per trade (dynamic lot, Half-Kelly with the AI) | `MAX_RISK_PER_TRADE_PERCENT` | Maestro |
| Risk Shield: rejects the trade if the minimum lot risks > 1.5% | `ABSOLUTE_MAX_TRADE_RISK_PERCENT` | Maestro |
| Risk at SL ≤ 2% and 3× margin reserve | `QUANT_MAX_RISK_PCT`, `QUANT_MARGIN_RESERVE_MULT` | Quant |
| 2% max daily loss (blocks entries; Maestro also closes the position) | `MAX_DAILY_LOSS_PERCENT`, `DAILY_MAX_LOSS_CLOSE_ENABLED` | Both |
| Spread filter (aborts if spread is too wide) | `MAX_SPREAD_POINTS`, `SYMBOL_MAX_SPREAD_POINTS` | Both |
| Locked breakeven (entry + spread + 1 tick) | `ENABLE_BREAKEVEN`, `BREAKEVEN_LOCK_SPREAD_MULT` | Maestro |
| Per-symbol trading window (e.g. HK50 22:15–01:00 BRT) | `SYMBOL_TRADING_HOURS` | Maestro |
| Minimum capital per symbol ("Garage Lock") | `MIN_BALANCE_REQUIREMENTS` | Maestro |
| **Closed** candles only (no decisions on a forming candle) | — | Both |

---

## 🧭 `bot.bat` commands

Quick tools to inspect the bot without opening large files. Each command returns the real exit code (0 = success).

| Command | What it does |
|---|---|
| `.\bot.bat quant` | **Starts Quant Mode** (HK50 H4 / US500 D1) |
| `.\bot.bat dashboard` | **Opens the live web dashboard** in the browser |
| `.\bot.bat diagnose` | MT5 connection, balance, margin and `bot.log` errors from the last 24h |
| `.\bot.bat market` | Price, spread, tick value and margin for configured symbols |
| `.\bot.bat config` | Risk %, daily loss, AI filter, **quant routes with the $ limit for the current balance**, and setups per symbol |
| `.\bot.bat positions` | Bot positions and virtual (paper) trades |
| `.\bot.bat performance` | Net profit and win rate for the last 7 days |
| `.\bot.bat tail` | Last 15 lines of the newest log (`%APPDATA%\mt5bot\logs`) |
| `.\bot.bat hardware` | CPU/RAM usage (requires `pip install psutil`) |
| `.\bot.bat backtest HK50 3` | Russian Setup backtest (symbol, months). Read-only. |
| `.\bot.bat train` | Retrains the XGBoost model |
| `.\bot.bat ask "question"` | Queries the project memory (RAG) |
| `.\bot.bat test` | Runs the test suite |
| `.\bot.bat ci` | Runs the same steps as CI locally (lint, tests, package and Maestro) |
| `.\bot.bat build` | Builds the Maestro (`maestro\maestro.exe`) |
| `.\bot.bat panic` | 🚨 **Closes all bot positions at market** (manual ones are kept) |

To view the Quant Mode log: `Get-Content $env:APPDATA\mt5bot\logs\quant_runner.log -Tail 20`

---

## ⚙️ Configuration

Defaults live in **`mt5bot/core/config.py`**. To change them without editing code, create **`%APPDATA%\mt5bot\config.toml`** (`bot.bat config` prints the exact path and tags each value that came from it with `[config.toml]`):

```toml
quant_max_risk_pct = 2.0          # max loss at SL, % of balance (routes' default)
max_daily_loss_percent = 2.0      # daily lock
ml_filter_enabled = true          # XGBoost veto on classic setups

[routes.US500]
max_risk_pct = 12.0               # this route's own limit
enabled = true                    # false turns the route off
```

Values with the wrong type or out of range are **refused with a warning** (naming the file and key) and the default is kept. Nothing crashes the bot.

The most important defaults in `config.py`:

```python
# Quant routes: (symbol) -> timeframe, setup and validated parameters
QUANT_ROUTES = {
    "HK50":  {"timeframe": "H4", "setup": "PULLB",  "params": {"sl_atr": 1.0, "tp_r": 2.0}},
    "US500": {"timeframe": "D1", "setup": "RSI2MR", "params": {"rsi_level": 5.0, "sl_atr": 2.0,
                                                              "long_only": False, "max_bars": 15},
              "max_risk_pct": 12.0},   # own limit: each stop ~10% of the account at $16
}
QUANT_MAX_RISK_PCT = 2.0           # max loss at SL, % of balance (a route may set its own "max_risk_pct")
QUANT_MARGIN_RESERVE_MULT = 3.0    # free margin that must remain (x position margin)

MAX_RISK_PER_TRADE_PERCENT = 1.0   # Maestro: risk per trade
MAX_DAILY_LOSS_PERCENT = 2.0       # daily lock
ML_FILTER_ENABLED = True           # XGBoost veto on classic setups
ML_MIN_WIN_PROB = 0.40
ASSET_SETUPS = {...}               # which classic setups run on each symbol
SYMBOL_TRADING_HOURS = {...}       # per-symbol trading window (BRT)
MAGIC = 20260731                   # identifies the bot's orders in MT5
```

> **Do not change quant route parameters without redoing the validation** ([see how](#-backtesting-and-strategy-research)). Tweaking a number to "improve" the past is the shortest road to overfitting.

---

## 📂 Data and logs

| File | Contents |
|---|---|
| `%APPDATA%\mt5bot\trades.json` | Trade history (entries, exits, real profit including commission and swap) |
| `%APPDATA%\mt5bot\virtual_rejections.json` | Rejected signals (risk, spread, AI), used by the Optimizer |
| `%APPDATA%\mt5bot\config.toml` | Your configuration (optional), on top of `config.py` defaults |
| `%APPDATA%\mt5bot\logs\quant_runner.log` | Quant Mode log |
| `%APPDATA%\mt5bot\logs\bot_YYYYMMDD.log` | Maestro/Brain logs |

The bot is **stateless**: if the PC restarts, it re-reads positions straight from MT5 and picks up where it left off.

---

## 🚨 Emergency: how to stop everything

1. **Stop the bot** so it does not reopen positions: **Ctrl+C** in the `bot.bat quant` window, or `/quit` in the Maestro.
2. **Close the bot's positions:** `.\bot.bat panic` (or `/quit close-all` in the Maestro).
3. If the PC freezes: positions opened by the bot already have an **SL on the broker's server**. Close them manually in MT5 (including the mobile app) if needed.

---

## 🔬 Backtesting and strategy research

**Russian Setup backtest** (read-only):

```powershell
.\bot.bat backtest HK50 3
```

**Redo the quant research** (with MT5 open; sends no orders):

```powershell
cd tools\quant_research
python fetch.py JP225,US500,FR40,AU200,HK50,USOIL+,ETHUSD,EU50,UK100   # download candles
python meta.py                                                          # costs and point value
python research.py HK50,US500 M15,H1,H4,D1 r_all.json                   # grid (~1 min)
python analyze.py r_all.json                                            # in-sample vs out-of-sample robustness
python deep.py                                                          # year by year + 1.5x spread
```

Before changing a route, require: profit **in both periods**, most variations of the family profitable, a max drawdown that fits your balance, and results that hold with 1.5× spread.

---

## 🤖 Machine Learning (XGBoost)

On classic setups, each signal carries a "snapshot" of the market: distances to moving averages, ADX, ATR, RSI, candle microstructure, time of day and more. An **XGBoost** model estimates the win probability and **vetoes** the trade below `ML_MIN_WIN_PROB`. Vetoed signals are still tracked as "phantom orders" and become training data.

- Models: `models/mt5bot_xgboost_<SYMBOL>_v*.json`.
- Retrain: `.\bot.bat train`.
- Quant Mode does **not** use XGBoost (it was not part of the validation).

---

## 📲 Telegram notifications

The logger sends alerts to Telegram when the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` variables exist. `.env.example` explains how to get the token (@BotFather) and the chat id. The bot **does not load the `.env` file by itself**, so set the variables in Windows:

```powershell
setx TELEGRAM_BOT_TOKEN "123456789:ABC..."
setx TELEGRAM_CHAT_ID "123456789"
# close and reopen the terminal
```

---

## 🏗️ Architecture

```
┌──────────────────────┐   JSON (stdin/stdout)   ┌───────────────────────────────┐
│  Maestro (Go, TUI)   │ ──────────────────────▶ │  Brain (Python)               │
│  supervises workers  │ ◀────────────────────── │  interfaces/brain_worker.py   │
│  /add /study /quit   │                         │   └─ execution_manager        │
└──────────────────────┘                         │       ├─ quant route ─▶ quant_manager
                                                 │       └─ classic ─────▶ strategy + filters + AI
┌──────────────────────┐                         │                               │
│ tools/quant_runner.py│ ──── manage_cycle ────▶ │  executor ──▶ MetaTrader 5    │
│   (bot.bat quant)    │                         └───────────────────────────────┘
└──────────────────────┘
```

- **Only Python talks to MT5.** The Maestro stays out of the order path.
- **Stateless:** each cycle derives its state from the positions and orders in MT5.

```
mt5_bot/
├── mt5bot/
│   ├── core/          config.py (all parameters), launcher, logger
│   ├── engine/        strategy.py (classic setups), quant_setups.py, indicators, scoring, trailing
│   ├── execution/     execution_manager.py, quant_manager.py, executor.py (orders)
│   ├── risk/          risk_calculator.py (lot size, locks, trading hours)
│   ├── data/          tracker.py (real trades), paper_tracker.py (virtual trades/rejections)
│   └── mentorship/    ml_xgboost.py, supervisor, optimizer, simulator
├── interfaces/        brain_worker.py (worker launched by the Maestro)
├── maestro/           Go Maestro (TUI); maestro.exe is built by bot.bat build
├── tools/             bot.bat tools, quant_runner.py, quant_research/, backtest.py
├── memoria/           permanent project memory (wiki + BM25 RAG, in Portuguese)
├── tests/             pytest suite (simulated MT5)
└── bot.bat            command toolkit
```

---

## 🩺 Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| `MT5: Falha` / `Falha ao conectar no MT5` | Terminal closed or logged out | Open MT5, log in and run `.\bot.bat diagnose` |
| Order error `10027` | **Algo Trading** turned off | Turn on the Algo Trading button (green) |
| Error `10016` (invalid stops) | SL too close to the price | Quant Mode already checks the *stops level*; on the Maestro, check the ATR/timeframe |
| `SPREAD FILTER REJECTED` | Spread above the limit (low liquidity) | Normal outside main hours; adjust `SYMBOL_MAX_SPREAD_POINTS` if it makes sense |
| `perda no SL $X > limite` | Trade would risk more than 2% of balance | The margin lock working as intended (e.g. HK50 with a very high ATR, or the balance dropped below what the route allows) |
| `SEM MARGEM` | Not enough free margin for the reserve | Close other positions or increase the balance |
| `SINAL EXPIRADO` | The bot started after the next candle opened | Normal; it waits for the next signal |
| `AGUARDANDO MERCADO` | Market closed or next candle not open yet | Wait (e.g. HK50 opens Sunday ~22:15 BRT) |
| `GARAGE LOCK` | Balance below the symbol's minimum on the Maestro | See `MIN_BALANCE_REQUIREMENTS` |
| `HORÁRIO FECHADO` | Outside the symbol's window on the Maestro | See `SYMBOL_TRADING_HOURS` |
| `.\bot.bat hardware` fails with `No module named psutil` | Optional dependency | `pip install psutil` |
| `bot.bat` not recognized in PowerShell | PowerShell does not run scripts from the current folder without a prefix | Use `.\bot.bat quant` |

---

## 🧪 Development

```powershell
.\bot.bat test                     # or: python -m pytest -q
```

- Tests use a **simulated MT5** (`tests/conftest.py`) and do not need the terminal open.
- Every logic change needs a test (`tests/test_*.py`).
- Log with `logging`, never `print()`, in the production path.
- Version history: [`CHANGELOG.md`](CHANGELOG.md) · Detailed architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

> [!NOTE]
> **Developing with AI?** Read [`AGENTS.md`](AGENTS.md) first. The project has a **permanent RAG memory** (`memoria/`) with the strategies' source books and every architecture decision. Query it with `.\bot.bat ask "your question"`.

---

<div align="center">

**MIT License** · Made by [Fabio Dornele](https://github.com/fabiodrneles)

*Don't chase price. Let math and risk management handle the rest.*

</div>
