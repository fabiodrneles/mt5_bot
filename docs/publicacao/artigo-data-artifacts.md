# Data Artifacts and False Discoveries in Retail Backtesting: Evidence from 128,000 Strategy Configurations

**DRAFT v0.1, 2026-10-24.** Not for distribution. Items marked `[TODO]` need the author's decision or verification before submission.

**Author:** `[TODO: full name, affiliation, e-mail, ORCID]`

**Target venues:** SSRN (Capital Markets: Market Microstructure; Econometric Modeling) and/or arXiv q-fin.TR / q-fin.ST. Code and protocol: `[TODO: GitHub URL + Zenodo DOI]`.

---

## Abstract

Retail traders and independent developers routinely evaluate trading rules on bar data supplied by their broker's platform. We ask whether any rule from a broad, literature-based library survives realistic costs and multiple-testing control in the setting of a very small real account (US$ 16) on a retail CFD/forex broker. We pre-register a decision protocol and test 128,076 configurations of 31 rule families (mean reversion, trend following, candlestick patterns, tick-volume rules, calendar effects and three rules proposed by a discretionary trader) on up to 337 instruments and five timeframes. We add exhaustive calendar scans (136,864 hour × weekday × instrument and day-of-month cells), cross-asset lead–lag tests (45,918 pairs) and cointegration-based pairs trading. Selection uses only the first 60% of each series, and acceptance requires out-of-sample profit, family robustness, a 1.5× cost stress test, anchored walk-forward, a Deflated Sharpe Ratio of at least 0.95 and a Monte Carlo ruin bound for the account. **No configuration passes all criteria**, and every family has a negative median out-of-sample t-statistic. Only one calendar cell survives false-discovery-rate control and out-of-sample checks, which is consistent with the expected number of false discoveries. Our main contribution is methodological: we document six **data artifacts** in broker bar data that manufacture spurious profitable strategies, each confirmed with one-minute bars or bid/ask ticks. Two examples are opening prints of equity CFDs that are not executable, and a `spread` field that stores the bar's minimum and hides rollover spikes of up to 7×. Uncorrected, these artifacts produced 64 apparently significant "daily patterns", including one with a t-statistic near 30. We also report a case study of a chart-reading rule, refined five times by its proponent, that is perfectly separable in-sample by construction and has no out-of-sample edge. One rule with prior academic support, a two-period RSI mean reversion on US equity indices, survives the corrected simulator. All code, the protocol and the tests are public; raw broker data are not redistributed.

**Keywords:** backtesting, data snooping, false discovery rate, deflated Sharpe ratio, market microstructure, retail trading, data quality, reproducibility.

**JEL:** G11, G12, G14, C12, C52.

---

## 1. Introduction

Backtests are the main evidence that retail traders and many independent developers use to decide whether to risk money. Two failure modes are well known in academic finance. The first is **data snooping**: when many rules are tried, some look good by chance [Sullivan, Timmermann & White 1999; White 2000; Harvey, Liu & Zhu 2016; Bailey et al. 2017]. The second is **cost underestimation**, which turns gross edges into net losses [Harris 2003].

A third failure mode receives much less attention outside market microstructure research: **artifacts in the data itself**. Retail platforms supply OHLC bars built from bid quotes, with summary fields (such as a per-bar spread) whose exact definition is rarely documented. A simulator that trusts these fields at face value can "trade" at prices nobody could obtain.

This paper reports a large, pre-registered search for exploitable patterns in the setting of a retail account. The study was motivated by a practical question from a discretionary trader with a US$ 16 account: *is there any repeating pattern, by time of day, date, indicator, volume or cross-asset behaviour, that leaves a profit after costs, even of a few cents?* We make three contributions:

1. **A catalogue of six data artifacts** in broker bar data, each with a diagnostic signature and confirmation from a finer, independent data source (§4). Uncorrected, they explain every "too good to be true" result in our first scans.
2. **A large negative result under explicit multiple-testing control** (§5). 128,076 configurations, 136,864 calendar cells and 45,918 lead–lag pairs yield no strategy that passes a pre-registered seven-criterion protocol, with one marginal calendar survivor.
3. **A case study in turning chart reading into testable rules** (§6). It shows why a rule can separate winners from losers perfectly in-sample and still have no predictive value, and it proposes a simple instrument, a signal journal, to measure discretionary skill without hindsight bias [Fischhoff 1975].

The engineering is part of the contribution. The pipeline is resumable, the simulator is covered by regression tests (including a no-look-ahead property test), and the protocol was versioned before the results were seen [Nosek et al. 2018].

## 2. Related work

`[TODO: expand to 1–1.5 pages.]`
- *Data snooping and multiple testing:* reality check and SPA tests [White 2000; Sullivan, Timmermann & White 1999]; the factor zoo and higher hurdles [Harvey, Liu & Zhu 2016]; deflated Sharpe ratio and probability of backtest overfitting [Bailey & López de Prado 2014; Bailey et al. 2017]; false discovery rate [Benjamini & Hochberg 1995].
- *Technical rules:* moving-average and breakout rules [Brock, Lakonishok & LeBaron 1992]; short-term reversal [De Bondt & Thaler 1985; Connors & Alvarez 2009]; time-series momentum [Moskowitz, Ooi & Pedersen 2012]; calendar effects [French 1980; Ariel 1987]; pairs trading [Gatev, Goetzmann & Rouwenhorst 2006].
- *Microstructure and costs:* [Harris 2003]; `[TODO: add a reference on bid/ask bar construction and rollover spreads in OTC FX]`.
- *Retail outcomes:* [Barber & Odean 2000; Chague, De-Losso & Giovannetti 2019].
- *Adaptive markets:* [Lo 2004].

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

**Calendar, lead–lag and pairs.** Of 136,864 calendar cells, 20 pass FDR in-sample and 1 passes all OOS checks: a long USDJPY position for one hour from 01:00 server time on Mondays (OOS t = 2.19, positive in every year). Unlike A2–A5, bid/ask ticks show a normal spread at that time, so it is not a cost artifact. With 20 rejections at $q = 5\%$, about one false discovery is expected. We classify it as an experimental candidate for forward testing, not as a finding. None of the 45,918 lead–lag pairs passes FDR, and all 15 cointegrated pairs lose after costs.

**What survives.** A two-period RSI mean-reversion rule on the S&P 500 CFD, selected in an earlier study, keeps its OOS profit under the corrected simulator (+US$ 9.73, t = 3.2). Applied **without re-optimisation** to all low-margin indices, it is significant on the US 500 (t = 2.48) and Nasdaq-100 (t = 2.10), positive on the Dow (t = 1.14), and weak or negative elsewhere. This is consistent with short-term reversal in US equity indices [Connors & Alvarez 2009]. A trend-pullback rule on the Hang Seng CFD, also from the earlier study, shrinks by about 40% once artifacts are removed.

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

`[TODO: convert to the venue's style.]` Ariel 1987; Bailey & López de Prado 2014; Bailey et al. 2017; Barber & Odean 2000; Benjamini & Hochberg 1995; Brock, Lakonishok & LeBaron 1992; Chague, De-Losso & Giovannetti 2019; Connors & Alvarez 2009; De Bondt & Thaler 1985; Efron & Tibshirani 1993; Fischhoff 1975; French 1980; Gatev, Goetzmann & Rouwenhorst 2006; Harris 2003; Harvey, Liu & Zhu 2016; Horner 2005; Lo 2004; Moskowitz, Ooi & Pedersen 2012; Nosek et al. 2018; Sullivan, Timmermann & White 1999; White 2000. Full entries: `docs/manual/referencias.md`.
