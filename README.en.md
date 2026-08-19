<div align="center">
  <img src="docs/assets/banner.jpg" alt="MT5Bot Maestro Banner" width="100%">
</div>

<br>

<div align="center">
  <strong>🌍 Read in:</strong> <a href="README.md">Português</a> | <strong>English</strong>
</div>

<br>

<div align="center">
  <strong>Quantitative Algorithmic Trading Platform with Predictive Machine Learning Filter</strong><br>
  <em>Institutional hybrid architecture focused on extreme risk mitigation and mathematical precision.</em>
</div>

<br>

<div align="center">
  <img src="https://img.shields.io/badge/Language-Go_%7C_Python-black?style=for-the-badge&logo=go&logoColor=FF7300" alt="Go/Python">
  <img src="https://img.shields.io/badge/AI_Engine-XGBoost-black?style=for-the-badge&logo=xgboost&logoColor=FF7300" alt="XGBoost">
  <img src="https://img.shields.io/badge/Platform-MetaTrader_5-black?style=for-the-badge&logo=metatrader&logoColor=FF7300" alt="MT5">
  <img src="https://img.shields.io/badge/License-MIT-black?style=for-the-badge&logoColor=FF7300" alt="MIT">
</div>

---

## ⬛ The Competitive Edge

Off-the-shelf MQL5 bots fail because they are optimized for a market that no longer exists (overfitting on illusory backtests).

**MT5Bot Maestro** adopts the philosophy of a *Quantitative Hedge Fund*: the primary goal is not to find a "magic setup," but to apply **brutal risk management**.
The position size never exceeds 1% of the account balance (`Dynamic Risk-Sizer`), and daily exposure is mathematically capped (`Max Daily Loss`). **This means your capital survives intact through the market's worst crashes and "black swans."**

---

## 🟧 Cutting-Edge Architecture: Maestro (Go) + Brain (Python)

Native MQL5 environments are obsolete for Artificial Intelligence and Data Science. **MT5Bot Maestro** was rebuilt on a revolutionary hybrid architecture:

* **Maestro (Golang)**: The orchestration core. Built in Go, it runs in the terminal with a low-latency *CLI TUI (Text User Interface)*. It manages the lifecycle of workers in parallel threads and provides *Crash-Loop Protection* (Stateless Recovery). If the system crashes or the PC reboots, it reassembles positions directly from the broker's server in under 5 seconds.
* **Brain (Python 3.10+)**: Where the heavy lifting occurs. Data Science libraries (Pandas/NumPy) slice the microstructure of thousands of candles, calculate VWAP crossovers, generate dynamic Scoring for each asset, and communicate directly with the Machine Learning engine.

---

## ⬛ Predictive Filter (XGBoost Machine Learning)

The baseline strategy gives you the rules, but it's the **Artificial Intelligence** that gives you a glimpse into the future. We implemented what we call a **Data Flywheel**.

When a mathematical setup triggers (e.g., Setup 9.1), the order is **not** immediately dispatched. The extractor captures 24 instantaneous variables from that exact second (Distance from SMA200, ADX Strength, ATR Volatility, Price Acceleration).
This matrix is fed into our **XGBoost (Decision Trees)** model, which answers a single binary, statistical question:

> *"Historically, when the market was breathing exactly like this, what was the probability of this trade returning a profit?"*

If the inferred probability is lower than `ML_MIN_WIN_PROB` (e.g., 40%), **the bot vetoes the operation**. You stop bleeding money on extreme consolidation days.
*(For MLOps engineers: The system features a Continuous Training Pipeline on Colab/GitHub Actions via virtual tracking files - Phantom Orders).*

---

## 🟧 The Business Card: Swiss Army Knife (CLI)

Time and processing power are crucial. We built a central CLI orchestrator (`bot.bat`) designed for **Senior Engineers** and **AI Agents** to perform system telemetry with zero effort, saving precious processing tokens.

Just open your terminal and type:

```powershell
bot.bat diagnose    # Full core Health Check and MT5 connectivity ping
bot.bat hardware    # Deep CPU/RAM telemetry and memory-leak prevention
bot.bat market      # Instant Volatility, Dynamic Spread, and Margin scanning
bot.bat config      # Audit of active % Risk and running algorithms
bot.bat positions   # Exposure Report (Real Orders and Phantom Trades)
bot.bat performance # Executive PnL (Net Profit) and WinRate report for the last 7 days
bot.bat tail        # Surgical log extraction, bypassing massive cat commands
bot.bat panic       # 🚨 PANIC BUTTON: Kill-Switch that liquidates all market exposure
bot.bat ask "X"     # Vector query on the repository's RAG memory (e.g., bot ask "9.1 rules")
bot.bat train       # Triggers local XGBoost engine retraining
bot.bat backtest    # Fires up the Local Financial Simulator (e.g., bot backtest HK50)
bot.bat test        # Unit Testing and Engine Mock Pipeline
python main.py      # 🔥 STARTS THE BOT IN PRODUCTION / LIVE TRADING MODE
```

---

## ⬛ Strategic Dictionary (The Decision Engine)

Maestro carries **11 Quantitative Strategies** that can operate simultaneously. If two strategies trigger on the same asset, the `scoring.py` module runs a probability matrix, picks the winner, and aborts the loser.

| Algorithm | Market Behavior and Dynamics |
| :--- | :--- |
| **Family 9.1 to 9.4** | Captures micro-trends and EMA9 pullbacks. Ideal for directional volatility. |
| **Ponto Contínuo (PC)** | Algorithmic sniper. Millimetric entries on the 21 SMA during an ongoing trend. |
| **Breakaway Gaps** | Exclusive routing for Indices (HK50). Exploits inefficiency and institutional panic at the Asian open. |
| **Russian Setup (Mean Reversion)** | Mean reversion using Bollinger Band deviations (FFFD) and RSI. Profits from extreme exhaustion. |
| **DiNapoli / SAR / IFR2** | Auxiliary routing for highly ranging markets and Forex. |

### 🛡️ Macro-Economic Shields
- **SMA50 / SMA200 Filter**: Orders against the macro trend are summarily ignored.
- **Spread Microstructure**: Entries with abusive transactional costs (dangerous slippage) are aborted before touching the broker.
- **Adaptive Trailing Stop**: Once in a trade, the bot defends it to the death. Reached 1x Risk? The Stop moves to `Breakeven` and you won't lose another cent. From there, it squeezes profit candle by candle until the flow reverses.

---

## 🟧 Deploying the Project (Clean Installation)

A robust environment shouldn't require painful configurations. To get this infrastructure running, you just need **Windows 10/11** (the MT5 Terminal is Windows exclusive) and **Python 3.10+**.

```bash
# 1. Clone the infrastructure
git clone https://github.com/fabiodrneles/mt5_bot.git
cd mt5_bot

# 2. Install dependencies (Data Core + MetaQuotes Driver)
pip install -e .

# 3. Keep your MT5 Terminal open and logged into your broker
# 4. Launch the Maestro Interactive Console
python main.py
```
> The *Text UI* dashboard will pop up on your screen. Type `/help` for internal manuals or `/add WIN M5` to fire up the mini-index engines right now.

---

## ⬛ AI-Driven Architecture (Permanent RAG Memory)

This software was sculpted in partnership with advanced Artificial Intelligence agents to ensure bulletproof code, elegant *Design Patterns*, and high-caliber architecture.

> [!CAUTION]
> **Notice for Artificial Intelligences:** If you (an AI) have just been summoned to develop this repository, suspend your immediate actions and read the master file `AGENTS.md`.
> This repository is equipped with a **Permanent RAG Memory (BM25)** — bypassing expensive *embeddings* and storing the entire technical context, statistical decisions, and core logic of the fund. Read the commandments in `AGENTS.md` before proposing any changes to the bot's nervous system.

---
<div align="center">
  <em>Don't chase the price. Let the math handle the rest.</em>
</div>
