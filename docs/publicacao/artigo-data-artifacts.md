# Data Artifacts and False Discoveries in Retail Backtesting: Evidence from 128,000 Strategy Configurations

**DRAFT v0.2, 2026-10-24.** Not for distribution. Items marked `[TODO]` need the author's decision or verification before submission.

**Author:** `[TODO: full name, affiliation, e-mail, ORCID]`

**Target venues:** SSRN (Capital Markets: Market Microstructure; Econometric Modeling) and/or arXiv q-fin.TR / q-fin.ST. Code and protocol: `[TODO: GitHub URL + Zenodo DOI]`.

---

## Abstract

Retail traders and independent developers routinely evaluate trading rules on bar data supplied by their broker's platform. We ask whether any rule from a broad, literature-based library survives realistic costs and multiple-testing control in the setting of a very small real account (US$ 16) on a retail CFD/forex broker. We pre-register a decision protocol and test 128,076 configurations of 31 rule families (mean reversion, trend following, candlestick patterns, tick-volume rules, calendar effects and three rules proposed by a discretionary trader) on up to 337 instruments and five timeframes. We add exhaustive calendar scans (136,864 hour × weekday × instrument and day-of-month cells), cross-asset lead–lag tests (45,918 pairs) and cointegration-based pairs trading. Selection uses only the first 60% of each series, and acceptance requires out-of-sample profit, family robustness, a 1.5× cost stress test, anchored walk-forward, a Deflated Sharpe Ratio of at least 0.95 and a Monte Carlo ruin bound for the account. **No configuration passes all criteria**, and every family has a negative median out-of-sample t-statistic. Only one calendar cell survives false-discovery-rate control and out-of-sample checks, which is consistent with the expected number of false discoveries. Our main contribution is methodological: we document six **data artifacts** in broker bar data that manufacture spurious profitable strategies, each confirmed with one-minute bars or bid/ask ticks. Two examples are opening prints of equity CFDs that are not executable, and a `spread` field that stores the bar's minimum and hides rollover spikes of up to 7×. Uncorrected, these artifacts produced 64 apparently significant "daily patterns", including one with a t-statistic near 30. We also report a case study of a chart-reading rule, refined five times by its proponent, that is perfectly separable in-sample by construction and has no out-of-sample edge. One rule with prior academic support, a two-period RSI mean reversion on US equity indices, survives the corrected simulator. Finally, we quantify a **minimum viable capital** for retail leveraged products. Because the smallest position carries a fixed money risk, a US$ 16 account must risk about 7.5% per trade even on the surviving rule. Reaching a prudent 1% risk level would take decades of trading profits but only weeks of modest contributions. All code, the protocol and the tests are public; raw broker data are not redistributed.

**Keywords:** backtesting, data snooping, false discovery rate, deflated Sharpe ratio, market microstructure, retail trading, data quality, reproducibility.

**JEL:** G11, G12, G14, C12, C52.

---

## 1. Introduction

Backtests are the main evidence that retail traders and many independent developers use to decide whether to risk money. Two failure modes are well known in academic finance. The first is **data snooping**: when many rules are tried, some look good by chance [Sullivan, Timmermann & White 1999; White 2000; Harvey, Liu & Zhu 2016; Bailey et al. 2017]. The second is **cost underestimation**, which turns gross edges into net losses [Harris 2003].

A third failure mode receives much less attention outside market microstructure research: **artifacts in the data itself**. Retail platforms supply OHLC bars built from bid quotes, with summary fields (such as a per-bar spread) whose exact definition is rarely documented. A simulator that trusts these fields at face value can "trade" at prices nobody could obtain.

This paper reports a large, pre-registered search for exploitable patterns in the setting of a retail account. The study was motivated by a practical question from a discretionary trader with a US$ 16 account: *is there any repeating pattern, by time of day, date, indicator, volume or cross-asset behaviour, that leaves a profit after costs, even of a few cents?* We make four contributions:

1. **A catalogue of six data artifacts** in broker bar data, each with a diagnostic signature and confirmation from a finer, independent data source (§4). Uncorrected, they explain every "too good to be true" result in our first scans.
2. **A large negative result under explicit multiple-testing control** (§5). 128,076 configurations, 136,864 calendar cells and 45,918 lead–lag pairs yield no strategy that passes a pre-registered seven-criterion protocol, with one marginal calendar survivor.
3. **A quantification of minimum viable capital** (§5.4). The discreteness of retail positions, not the choice of strategy, binds small accounts, and contributions dominate returns below that threshold.
4. **A case study in turning chart reading into testable rules** (§6). It shows why a rule can separate winners from losers perfectly in-sample and still have no predictive value, and it proposes a simple instrument, a signal journal, to measure discretionary skill without hindsight bias [Fischhoff 1975].

The engineering is part of the contribution. The pipeline is resumable, the simulator is covered by regression tests (including a no-look-ahead property test), and the protocol was versioned before the results were seen [Nosek et al. 2018].

## 2. Theoretical framework

### 2.1 Efficient and adaptive markets

The efficient-market hypothesis holds that prices reflect available information, so that rules based on past prices should not earn abnormal returns after costs [Fama 1970]. The adaptive-markets view relaxes this: profitable rules can exist for a while, but they shrink as participants learn and capital flows in, and their profitability changes with market conditions [Lo 2004]. Both views predict the same thing for **old, public and simple rules traded by small participants**: any remaining edge should be small relative to transaction costs. That is the null hypothesis of this study.

### 2.2 Evidence on technical and calendar rules

Early tests found predictive power in moving-average and trading-range breakout rules on the Dow Jones index [Brock, Lakonishok & LeBaron 1992]. Later work showed that much of this evidence disappears once the search over rules is accounted for [Sullivan, Timmermann & White 1999]. Short-horizon reversal is among the better documented effects [De Bondt & Thaler 1985]. It is the basis of the RSI(2) rules popularised for equity indices [Connors & Alvarez 2009]. Time-series momentum is documented across asset classes at monthly horizons [Moskowitz, Ooi & Pedersen 2012]. Calendar anomalies, such as the weekend effect [French 1980] and the turn-of-the-month effect [Ariel 1987], were widely reported and have weakened since publication. Pairs trading rests on cointegration [Engle & Granger 1987] and was profitable in US equities over long samples [Gatev, Goetzmann & Rouwenhorst 2006]. Practitioner methods, such as candlestick patterns, tick-volume indicators and trend-angle reading [Horner 2005], are rarely tested out of sample. This study does so.

### 2.3 Data snooping and multiple testing

When $m$ rules are tested at level $\alpha$, about $m\alpha$ false positives are expected under the null. The reality check and its extensions test the best rule against the whole search [White 2000; Sullivan, Timmermann & White 1999]. In cross-sectional asset pricing, the number of published factors led to proposals of t-statistic hurdles near 3 instead of 2 [Harvey, Liu & Zhu 2016]. For strategy research, the Deflated Sharpe Ratio corrects an observed Sharpe ratio for the number of trials and for non-normal returns [Bailey & López de Prado 2014]. The probability of backtest overfitting estimates how often the in-sample winner underperforms out of sample [Bailey et al. 2017]. Walk-forward and purged validation reduce the leakage of information between estimation and test samples [López de Prado 2018]. When thousands of homogeneous hypotheses are tested, as in calendar scans, controlling the false discovery rate is more informative than family-wise control [Benjamini & Hochberg 1995]. We combine these tools with pre-registration, a practice that limits researcher degrees of freedom [Nosek et al. 2018].

### 2.4 Transaction costs and market microstructure

Quoted prices are not transaction prices. A trade pays the bid–ask spread, and in OTC forex and CFDs the spread widens sharply around the daily rollover, at session opens and after weekends [Harris 2003]. Retail platforms summarise this activity into bars built from one side of the book, usually the bid. Their per-bar summaries hide the intra-bar distribution of costs. This is why our audit compares bars with one-minute data and with bid/ask ticks. Bootstrap resampling [Efron & Tibshirani 1993] is used to turn out-of-sample trade distributions into ruin probabilities.

### 2.5 Position sizing, ruin and discreteness

The Kelly criterion gives the bet fraction that maximises long-run geometric growth, $f^* = p - (1-p)/b$ for a bet won with probability $p$ at odds $b$ [Kelly 1956]. It has been extended to investment and trading [Thorp 2006; MacLean, Thorp & Ziemba 2011]. Two results matter for small accounts. First, sizing **multiplies** an edge and cannot create one: with $f^* \le 0$ the optimal fraction is zero. Second, the classical ruin problem shows that the probability of ruin falls quickly as capital grows relative to the stake [Feller 1968]. Retail derivatives add a constraint the textbook problem ignores: **the stake is discrete**. The smallest position has a fixed money risk, so below some capital level the trader cannot choose a prudent fraction (§5.4).

### 2.6 Retail traders and hindsight

Most active retail traders underperform [Barber & Odean 2000]. In Brazil, nearly all individuals who day-traded futures persistently lost money [Chague, De-Losso & Giovannetti 2019]. European regulators restricted retail leverage on CFDs after documenting widespread losses [ESMA 2018]. A plausible behavioural channel is hindsight bias: once the outcome is known, it appears to have been predictable [Fischhoff 1975]. This motivates our case study (§6) and the signal journal as a way to measure discretionary skill before outcomes are known.

## 3. Setting, data and methodology

### 3.1 Setting

A real account at a retail broker (MetaTrader 5, hedging, leverage 1:500, balance US$ 16) trading at the minimum lot. The universe is every tradable symbol whose minimum-lot margin is at most 25% of the balance: **337 of 465** instruments, covering forex, equity-index CFDs, commodities, crypto and single-stock CFDs. Data come from the broker's terminal: H1 (up to 30,000 bars), D1 (up to 4,000), H4 resampled from H1, and M15 (up to 40,000; forex, indices, commodities and crypto only) with M30 resampled from it. Volume is tick volume; the platform reports zero real volume for all CFDs.

### 3.2 Cost model and execution rules

For a long position at the minimum lot,

$$\pi = (P^{bid}_{exit} - P^{ask}_{entry})\,u - C + S, \qquad P^{ask} = P^{bid} + s,$$

where $u$ is the US$ value of one price unit at the minimum lot (from the platform's profit calculator), $s$ the spread, $C$ the commission and $S$ the swap. Swap is charged on each weekday rollover, with a triple charge on the broker's designated day. Signals are computed on closed bars and filled at the next bar's open. When a bar touches both stop and target, the stop is assumed first, and a gap through the stop fills at the open. The conservative entry rules added after the artifact audit (§4) are part of the simulator and are covered by tests.

### 3.3 Rule library

Twenty-eight families with 2–12 parameter variants each: RSI(2), RSI(n), IBS, consecutive closes, Double-7, Bollinger and z-score reversion, gap fade, Donchian, moving-average cross, time-series momentum, MACD, Keltner, Supertrend, ADX pullback, EMA20 pullback, NR7, inside bar, engulfing, pin bar, tick-volume capitulation and breakout, OBV with RSI(2), intraday VWAP, opening-range breakout, turn of the month, day of week and hour of day. Fast reversion rules also have intraday variants that close at day end. Three more families encode rules proposed by the discretionary trader (§6), including one inspired by the 34-EMA wave and slope ("clock angle") approach [Horner 2005].

### 3.4 Pre-registered acceptance protocol

Written and committed before any grid was run. Parameter selection uses only the first 60% of each series (IS), by the t-statistic of profit per trade (≥ 20 IS trades). A configuration is accepted only if it passes all seven criteria:

1. OOS: ≥ 30 trades, profit > 0, profit factor ≥ 1.2, t ≥ 2.
2. IS profit > 0.
3. Family robustness: ≥ 50% of the family's variants profitable in both IS and OOS.
4. OOS profit > 0 with costs × 1.5.
5. Anchored walk-forward, 5 folds re-selecting parameters: positive sum and ≥ 3 positive folds.
6. Deflated Sharpe Ratio ≥ 0.95 [Bailey & López de Prado 2014], with $N$ = number of configurations tested in the timeframe.
7. Account viability: median stop loss ≤ US$ 1.60 and 2-year ruin probability < 5% in a bootstrap Monte Carlo of OOS trades [Efron & Tibshirani 1993].

Calendar and lead–lag scans use Benjamini–Hochberg FDR at $q = 5\%$ on IS p-values, then require OOS t ≥ 2, profit in ≥ 70% of years and profit under 1.5× costs. All amendments made during execution are dated in the protocol, and each one made the simulator more conservative. One amendment concerns the estimator of $V[\widehat{SR}]$ in the DSR: a robust MAD-based estimate replaces the raw variance, which is dominated by degenerate configurations. We report both, and note that the robust estimator is the *less* strict of the two.

## 4. Data artifacts

Every result that looked "too good to be true" was treated as a suspected artifact and audited with a finer, independent source. Table 1 summarises the six cases.

**Table 1. Data artifacts found in broker bar data.**

| # | Symptom in the backtest | Cause | Evidence | Correction |
|---|---|---|---|---|
| A1 | Equity CFDs lose ≈ US$ 1 per trade under any rule | Per-lot commission applied to a 1-share lot | Per-trade Sharpe ≈ −34 (every trade loses exactly the cost) | Commission modelled as 0.1% of notional per side (estimated; not exposed by the API) |
| A2 | FX "profits" from buying at hour 1 and from "gap fades" around midnight | Rollover spread underestimated | AUDCAD median spread 3 pts normally, 19 at hour 0, 6 at hour 1 | Entry pays the larger spread of the previous and the entry bar |
| A3 | "Buy AUD on Monday": +US$ 411 OOS | Weekend-reopen spread | Median 62 pts on the first bar after the weekend (3 normally) | D1 entries pay the opening-hour and reopen spreads |
| A4 | "Buy US stocks at the New York open": t ≈ 30, profitable every day for years | **Non-executable opening print** in the H1 history | LKQ, 2023: bar body +1.053 and gap −1.096 on average; on recent M1 data the first real hour rises only US$ 0.018 | First bar after a session pause enters at the worse of open and previous close |
| A5 | "Buy EURUSD/EURGBP on Thursday at 00:00" (3 FDR survivors) | The bar's `spread` field stores the **minimum** spread of the bar | Bid/ask ticks for EURGBP, 00:00–00:10 on Thursdays: 82–224 pts, against ≈ 30 in the bar | No entries during the rollover hour |
| A6 | "LKQ daily, buy on Friday": DSR 0.86–0.99 depending on $N$, walk-forward 5/5 | The D1 bar inherits the opening print of A4 | Every weekday "rises" ≈ US$ 0.60 with an opposite gap; D1 open equals the first H1 open on 1,943/1,943 days; 37 of 72 CFDs affected, no FX or crypto | D1 entries at the worse of open and previous close |

**A diagnostic recipe.** The six cases were found with the same steps:

1. **Distrust implausible effect sizes.** A t of 30 for an hour-of-day rule on a liquid stock contradicts everything known about such markets.
2. **Decompose the return** into body ($C_t - O_t$) and gap ($O_t - C_{t-1}$). A fake open shows the signature $\mathbb{E}[C_t - O_t] \approx -\mathbb{E}[O_t - C_{t-1}]$.
3. **Test generality.** An artifact shows up on every weekday or hour, while a genuine calendar effect is specific.
4. **Confirm with an independent, finer source.** One-minute bars (A4) and bid/ask ticks (A5). A5 is invisible even in one-minute bars, whose spread field is also a minimum.

The sequence of calendar scans illustrates the stakes: 64 → 3 → 0 apparently significant patterns after the corrections for A4, A5 and A6. **Implication for practitioners:** the per-bar `spread` field of retail platforms is a summary statistic, not a transaction cost, and opening prints of CFDs on non-24h underlyings need verification before use.

## 5. Results

### 5.1 Grid

**Table 2. Grid funnel (31 families).**

| TF | Instruments | Configurations | Cells | 1 | 1–2 | 1–3 | 1–7 |
|---|---|---|---|---|---|---|---|
| D1 | 331 | 30,098 | 6,756 | 5 | 1 | 1 | 0 |
| H4 | 331 | 26,706 | 7,806 | 20 | 10 | 8 | 0 |
| H1 | 337 | 52,721 | 10,832 | 26 | 18 | 8 | 0 |
| M30 | 88 | 9,254 | 2,685 | 8 | 7 | 5 | 0 |
| M15 | 88 | 9,297 | 2,723 | 7 | 5 | 5 | 0 |
| **Total** | | **128,076** | **30,802** | **66** | **41** | **27** | **0** |

All 27 candidates that reached criteria 4–7 fail the DSR (maximum 0.049). Most also fail account viability: the largest OOS profits (US$ 118–157) carry stop losses of US$ 5–12 and 25–54% ruin probability. Every family has a negative median OOS t-statistic, from −0.48 (ADX pullback) to −5.86 (intraday IBS). `[TODO: Figure 1, distribution of OOS t by family.]`

### 5.2 Calendar, lead–lag and pairs

Of 136,864 calendar cells, 20 pass FDR in-sample and 1 passes all OOS checks: a long USDJPY position for one hour from 01:00 server time on Mondays (OOS t = 2.19, positive in every year). Unlike A2–A5, bid/ask ticks show a normal spread at that time, so it is not a cost artifact. With 20 rejections at $q = 5\%$, about one false discovery is expected. We classify it as an experimental candidate for forward testing, not as a finding. None of the 45,918 lead–lag pairs passes FDR, and all 15 cointegrated pairs lose after costs.

### 5.3 What survives

A two-period RSI mean-reversion rule on the S&P 500 CFD, selected in an earlier study, keeps its OOS profit under the corrected simulator (+US$ 9.73, t = 3.2). Applied **without re-optimisation** to all low-margin indices, it is significant on the US 500 (t = 2.48) and Nasdaq-100 (t = 2.10), positive on the Dow (t = 1.14), and weak or negative elsewhere. This is consistent with short-term reversal in US equity indices [Connors & Alvarez 2009]. A trend-pullback rule on the Hang Seng CFD, also from the earlier study, shrinks by about 40% once artifacts are removed.

### 5.4 Minimum viable capital

The account in this study has US$ 16. For the one rule that survives (US 500 RSI(2)), the median stop loss at the minimum lot is US$ 1.23, so **every trade risks about 7.5% of the account**. Practitioner guidance and the ruin results in §2.5 point to 1–2% per trade. We define the **minimum viable capital** of an instrument as the capital at which the minimum position risks a target fraction $\rho$:

$$C_{\min} = \frac{L_{\min}}{\rho},$$

where $L_{\min}$ is the money lost at the stop with the minimum lot. Using a one-day ATR stop as a reference, Table 4 gives $C_{\min}$ by asset class at the study's broker.

**Table 4. Minimum viable capital by asset class (median over instruments; one daily ATR stop at the minimum lot).**

| Asset class | Instruments | $L_{\min}$ (median) | $C_{\min}$ at $\rho = 1\%$ | $C_{\min}$ at $\rho = 2\%$ |
|---|---|---|---|---|
| Equity CFDs | 313 | US$ 0.36 | US$ 36 | US$ 18 |
| Equity indices | 19 | US$ 1.57 | US$ 157 | US$ 79 |
| Crypto | 43 | US$ 5.67 | US$ 567 | US$ 284 |
| Forex | 60 | US$ 6.01 | US$ 601 | US$ 301 |
| Commodities | 29 | US$ 74.78 | US$ 7,478 | US$ 3,739 |

Below $C_{\min}$, a trader can either take a risk fraction far above $\rho$ or not trade. The surviving rule earns about **0.87 R per year** (5.4 trades per year at an expectancy of 0.16 R). The expected annual return is therefore about $0.87\,\rho$: roughly 0.9% per year at $\rho = 1\%$ and 6.5% per year at the 7.5% that the US$ 16 account is forced to take, with correspondingly higher drawdowns. In money, the rule earns about US$ 1.26 per year at the minimum lot. Starting from US$ 16, reaching $C_{\min} \approx$ US$ 123 for this index at $\rho = 1\%$ would take on the order of **85 years** from trading profits alone, because the position cannot grow in steps smaller than the minimum lot. A monthly contribution of US$ 50 closes the same gap in about two months.

Three implications follow. First, **percentage returns do not depend on capital once the position is divisible**: the edge per unit of risk is what it is, and a larger account does not earn a higher percentage. Second, what a small account lacks is **the freedom to choose risk**. It is forced into either over-betting, with high ruin probability, or inactivity. Third, **for small accounts, contributions dominate strategy returns** by orders of magnitude. The binding constraint is minimum position size, not the rule. This is a structural feature of retail leveraged products, not a statement about investing in general: instruments with fractional units and no leverage, such as many funds and ETFs, have no comparable minimum.

## 6. Case study: turning chart reading into testable rules

A discretionary trader challenged the negative result with a real trade: on the US 500, M15 chart, a bearish bar closing below the 9-period EMA paid twice the risk. We tested the rule and five successive refinements proposed by the trader (Table 3). Each was evaluated signal by signal, with selection on the first 60% of signals.

**Table 3. Successive refinements of an EMA(9) cross rule (US 500 M15 unless noted).**

| Version | Refinement | Out-of-sample outcome |
|---|---|---|
| 1 | Close crosses EMA(9); target 2× bar range | The cited trade exists (+US$ 0.09). Same day: 20 signals, 2 winners. Full history: 1,994 trades, 32.9% hit rate against 33.3% break-even; −US$ 19.09 with costs, −US$ 7.65 without |
| 2 | Stop at bar extreme; tick-volume, trend and higher-timeframe filters (135 combinations) | Best IS combination: +US$ 4.49 IS, −US$ 0.05 OOS; 10/130 positive in both periods |
| 3 | "Find the filter that selects only the winners" (19,286 one- and two-condition rules on 12 features) | 4 rules separate the day's winners perfectly; on all other days all 4 lose. IS-learned rule: +US$ 8.44 → −US$ 3.68 OOS |
| 4 | Only after a strong prior trend; pause after stop streaks; similarity to past winners (k-NN) | 72 trend definitions × 15 markets: no OOS t ≥ 2; 0 variants profitable in both periods for k-NN, pauses and regime filters |
| 5 | "Any profit" exits; trend strength by slope angle [Horner 2005] | 55–65% of signals touch a profit before the stop, but no ex-ante exit captures it (first profitable close: 54% hit rate, mean win US$ 0.042 against mean loss US$ 0.077); slope-angle filters: no robust variant |

Two observations generalise. First, **with many candidate filters and few cases, perfect in-sample separation is guaranteed**. It is combinatorics, not prediction. Second, the trader's own labelled examples contradicted the stated criterion: the signal labelled "bad" had the strongest measured prior trend and also won. Rather than dismiss discretionary skill, we built a **signal journal**. The trader records a signal before its outcome, the system timestamps it, stores the executable price, measures the result on one-minute data, and compares "good" against "bad" labels with an exact binomial test against break-even. Skill, if present, will show up there without hindsight bias [Fischhoff 1975].

## 7. Discussion and limitations

Three forces explain the negative result. Costs are fixed per trade while useful movement shrinks with the horizon, and about 90% of calendar cells have a mean gross move below the mean cost. Public rules have been exploited for decades [Lo 2004]. And with 128,076 configurations, thousands of in-sample "winners" are expected by chance.

**Limitations.** Commission on equity CFDs is estimated. The conservative entry rules suppress genuine index gaps by construction. H1 and M15 histories are short (about 4–5 and 1–2 years). Results come from a single broker. Tick volume is not traded volume. The effective number of independent trials in the DSR is unobservable, and we use the most conservative choice and report the sensitivity. `[TODO: discuss what would change with larger accounts — granularity of lot sizes.]`

**Ethics and disclosure.** This is research, not investment advice. AI coding assistants were used in development and writing. Correctness was checked with automated tests, CI and reproduction of earlier published numbers. `[TODO: final wording per venue policy.]`

## 8. Reproducibility

The resumable pipeline (`tools/quant_research/pipeline2.py`), the protocol (`PROTOCOLO2.md`), the per-step state file and the simulator tests (`tests/test_research2.py`) are public. Raw broker data are not redistributed; any account on a MetaTrader 5 broker can regenerate them with the provided fetch scripts. `[TODO: tag a release and mint a Zenodo DOI.]`

## References

Format: ABNT, as in the technical guide. `[TODO: convert to the venue's style, e.g. APA or Chicago author-date.]`

- **[Ariel 1987]** ARIEL, R. A. A Monthly Effect in Stock Returns. *Journal of Financial Economics*, v. 18, n. 1, p. 161–174, 1987.
- **[Bailey & López de Prado 2014]** BAILEY, D. H.; LÓPEZ DE PRADO, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality. *The Journal of Portfolio Management*, v. 40, n. 5, p. 94–107, 2014.
- **[Bailey et al. 2017]** BAILEY, D. H.; BORWEIN, J. M.; LÓPEZ DE PRADO, M.; ZHU, Q. J. The Probability of Backtest Overfitting. *Journal of Computational Finance*, v. 20, n. 4, p. 39–69, 2017.
- **[Barber & Odean 2000]** BARBER, B. M.; ODEAN, T. Trading Is Hazardous to Your Wealth: The Common Stock Investment Performance of Individual Investors. *The Journal of Finance*, v. 55, n. 2, p. 773–806, 2000.
- **[Benjamini & Hochberg 1995]** BENJAMINI, Y.; HOCHBERG, Y. Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society: Series B*, v. 57, n. 1, p. 289–300, 1995.
- **[Brock, Lakonishok & LeBaron 1992]** BROCK, W.; LAKONISHOK, J.; LeBARON, B. Simple Technical Trading Rules and the Stochastic Properties of Stock Returns. *The Journal of Finance*, v. 47, n. 5, p. 1731–1764, 1992.
- **[Chague, De-Losso & Giovannetti 2019]** CHAGUE, F.; DE-LOSSO, R.; GIOVANNETTI, B. *Day Trading for a Living?* Working paper. São Paulo: FEA-USP, 2019. Disponível em: SSRN 3423101.
- **[Connors & Alvarez 2009]** CONNORS, L.; ALVAREZ, C. *Short Term Trading Strategies That Work*. Jersey City: TradingMarkets Publishing, 2009.
- **[De Bondt & Thaler 1985]** DE BONDT, W. F. M.; THALER, R. Does the Stock Market Overreact? *The Journal of Finance*, v. 40, n. 3, p. 793–805, 1985.
- **[Efron & Tibshirani 1993]** EFRON, B.; TIBSHIRANI, R. J. *An Introduction to the Bootstrap*. New York: Chapman & Hall, 1993.
- **[Engle & Granger 1987]** ENGLE, R. F.; GRANGER, C. W. J. Co-Integration and Error Correction: Representation, Estimation, and Testing. *Econometrica*, v. 55, n. 2, p. 251–276, 1987.
- **[ESMA 2018]** EUROPEAN SECURITIES AND MARKETS AUTHORITY. Decision (EU) 2018/796 of 22 May 2018 to temporarily restrict contracts for differences in the Union in accordance with Article 40 of Regulation (EU) No 600/2014. *Official Journal of the European Union*, L 136, 1 jun. 2018.
- **[Fama 1970]** FAMA, E. F. Efficient Capital Markets: A Review of Theory and Empirical Work. *The Journal of Finance*, v. 25, n. 2, p. 383–417, 1970.
- **[Feller 1968]** FELLER, W. *An Introduction to Probability Theory and Its Applications*. v. 1. 3. ed. New York: Wiley, 1968.
- **[Fischhoff 1975]** FISCHHOFF, B. Hindsight ≠ Foresight: The Effect of Outcome Knowledge on Judgment Under Uncertainty. *Journal of Experimental Psychology: Human Perception and Performance*, v. 1, n. 3, p. 288–299, 1975.
- **[French 1980]** FRENCH, K. R. Stock Returns and the Weekend Effect. *Journal of Financial Economics*, v. 8, n. 1, p. 55–69, 1980.
- **[Gatev, Goetzmann & Rouwenhorst 2006]** GATEV, E.; GOETZMANN, W. N.; ROUWENHORST, K. G. Pairs Trading: Performance of a Relative-Value Arbitrage Rule. *The Review of Financial Studies*, v. 19, n. 3, p. 797–827, 2006.
- **[Harris 2003]** HARRIS, L. *Trading and Exchanges: Market Microstructure for Practitioners*. New York: Oxford University Press, 2003.
- **[Harvey, Liu & Zhu 2016]** HARVEY, C. R.; LIU, Y.; ZHU, H. … and the Cross-Section of Expected Returns. *The Review of Financial Studies*, v. 29, n. 1, p. 5–68, 2016.
- **[Horner 2005]** HORNER, R. *Forex Trading for Maximum Profit: The Best Kept Secrets of the World's Biggest Market*. Hoboken: Wiley, 2005.
- **[Kelly 1956]** KELLY, J. L. A New Interpretation of Information Rate. *Bell System Technical Journal*, v. 35, n. 4, p. 917–926, 1956.
- **[Lo 2004]** LO, A. W. The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective. *The Journal of Portfolio Management*, v. 30, n. 5, p. 15–29, 2004.
- **[López de Prado 2018]** LÓPEZ DE PRADO, M. *Advances in Financial Machine Learning*. Hoboken: Wiley, 2018.
- **[MacLean, Thorp & Ziemba 2011]** MacLEAN, L. C.; THORP, E. O.; ZIEMBA, W. T. (ed.). *The Kelly Capital Growth Investment Criterion: Theory and Practice*. Singapore: World Scientific, 2011.
- **[Moskowitz, Ooi & Pedersen 2012]** MOSKOWITZ, T. J.; OOI, Y. H.; PEDERSEN, L. H. Time Series Momentum. *Journal of Financial Economics*, v. 104, n. 2, p. 228–250, 2012.
- **[Nosek et al. 2018]** NOSEK, B. A.; EBERSOLE, C. R.; DeHAVEN, A. C.; MELLOR, D. T. The Preregistration Revolution. *Proceedings of the National Academy of Sciences*, v. 115, n. 11, p. 2600–2606, 2018.
- **[Sullivan, Timmermann & White 1999]** SULLIVAN, R.; TIMMERMANN, A.; WHITE, H. Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *The Journal of Finance*, v. 54, n. 5, p. 1647–1691, 1999.
- **[Thorp 2006]** THORP, E. O. The Kelly Criterion in Blackjack, Sports Betting and the Stock Market. In: ZENIOS, S. A.; ZIEMBA, W. T. (ed.). *Handbook of Asset and Liability Management*. v. 1. Amsterdam: North-Holland, 2006. p. 385–428.
- **[White 2000]** WHITE, H. A Reality Check for Data Snooping. *Econometrica*, v. 68, n. 5, p. 1097–1126, 2000.
