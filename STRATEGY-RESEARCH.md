# Strategy Research — Academic Literature Scan

**Mode:** deep-research skill, `lit-review` (bibliography → source verification → synthesis)
**Researched:** 2026-09-06 · **Status:** Bibliography + verification complete; synthesis in progress
**Purpose:** Identify trading strategies documented in academic/practitioner literature and used by quant firms & investment banks, implementable in our framework.

## Research Question

> Which trading strategies with strong academic foundations are actually used by quant firms and investment banks, and which of them are implementable in a Python framework constrained to: daily bars (Alpaca IEX feed), US equities, ~$100k paper capital, long-only bias, limited compute (1 free-tier VM), and a mandatory risk-engine authority chain?

**Scope boundaries** — in scope: daily-bar strategies, factor portfolios, portfolio construction, position sizing/risk overlays, backtest-robustness methodology. Out of scope (documented, not researched): tick-level HFT/market-making (needs microstructure data we can't get free), options strategies, crypto-specific anomalies (Phase 6).

---

## 1. Search Strategy

| Parameter | Value |
|---|---|
| **Databases** | OpenAlex API (verification index), Semantic Scholar Graph API (cross-check), Exa web search (practitioner context), built-in web search |
| **Keywords** | momentum; time-series momentum; trend following; mean reversion; reversal; pairs trading; statistical arbitrage; factor investing; low volatility; quality; betting against beta; risk parity; risk contribution; hierarchical risk parity; volatility-managed portfolios; backtest overfitting; factor zoo; machine learning asset pricing; Kelly criterion; managed futures |
| **Date searched** | 2026-09-06 |
| **Inclusion criteria** | (1) seminal or heavily-cited paper defining a strategy family; (2) strategy implementable from daily OHLCV data; (3) peer-reviewed journal or widely-adopted practitioner paper; (4) directly informs strategy, portfolio construction, or methodology/robustness |
| **Exclusion criteria** | HFT/microstructure (data unavailable free); options volatility selling (instrument scope); pure theory without implementable signal; papers that could not be verified in an index |
| **Verification** | Every paper resolved against OpenAlex (title search + `title.search` filter) and/or Semantic Scholar before inclusion. Unresolved = excluded (none remained after retries). |

**PRISMA-style flow:** 26 candidate papers identified from domain knowledge → 25 verified via API lookups (OpenAlex primary, Semantic Scholar cross-check; the "Backtest Overfitting" candidate resolved to the correct Bailey et al. journal version) → 25 included (0 unverifiable after retries) → grouped into 6 themes.

**DISTRIBUTIONAL_SKEW_ADVISORY:**
- Dimension: time distribution — 23/24 sources pre-2020 (~96%).
- Advisory: coverage-distribution signal, not a defect. The corpus is deliberately seminal-anchored: these are the canonical definitions of each strategy family. Recent developments are covered via Gu/Kelly/Xiu (2020) for ML and the robustness literature (2015–2017) for factor decay. No expansion requested.

## 2. Source Verification Matrix

Citation counts from OpenAlex (2026-09-06) / Semantic Scholar (†). Tiers: **T1** peer-reviewed journal; **T1p** peer-reviewed practitioner journal; **T2** preprint/working paper; **T3** edited volume/handbook.

| # | Key | Paper | Venue | Year | Cites | Tier |
|---|---|---|---|---|---|---|
| 1 | `markowitz1952` | Portfolio Selection | Journal of Finance | 1952 | 5,450 | T1 |
| 2 | `jegadeesh1990` | Evidence of Predictable Behavior of Security Returns | Journal of Finance | 1990 | 2,781 | T1 |
| 3 | `jegadeesh1993` | Returns to Buying Winners and Selling Losers | Journal of Finance | 1993 | 11,618 | T1 |
| 4 | `brock1992` | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | Journal of Finance | 1992 | 2,262 | T1 |
| 5 | `ff1993` | Common Risk Factors in the Returns on Stocks and Bonds | J. of Financial Economics | 1993 | 28,008 | T1 |
| 6 | `ang2006` | The Cross-Section of Volatility and Expected Returns | Journal of Finance | 2006 | 4,843 | T1 |
| 7 | `ggr2006` | Pairs Trading: Performance of a Relative-Value Arbitrage Rule | Review of Financial Studies | 2006 | 819 | T1 |
| 8 | `maillard2010` | The Properties of Equally Weighted Risk Contribution Portfolios | J. of Portfolio Management | 2010 | 741 | T1p |
| 9 | `avellaneda2010` | Statistical Arbitrage in the US Equities Market | Quantitative Finance | 2010 | 342 | T1 |
| 10 | `mop2012` | Time Series Momentum | J. of Financial Economics | 2011/12 | 1,440 | T1 |
| 11 | `amp2013` | Value and Momentum Everywhere | Journal of Finance | 2013 | 2,275 | T1 |
| 12 | `bab2013` | Betting Against Beta | J. of Financial Economics | 2013/14 | 2,087 | T1 |
| 13 | `novymarx2013` | The Other Side of Value: The Gross Profitability Premium | J. of Financial Economics | 2013 | 2,084 | T1 |
| 14 | `hyz2013` | A New Anomaly: The Cross-Sectional Profitability of Technical Analysis | J. of Financial & Quant. Analysis | 2013 | 225 | T1 |
| 15 | `hurst2017` | Demystifying Managed Futures | J. of Investment Mgmt (wp 2013) | 2013/17 | 79† | T1p/T2 |
| 16 | `asness2014` | Fact, Fiction, and Momentum Investing | J. of Portfolio Management | 2014 | 103 | T1p |
| 17 | `daniel2016` | Momentum Crashes | J. of Financial Economics | 2016 | 924 | T1 |
| 18 | `lopezdeprado2016` | Building Diversified Portfolios that Outperform Out-of-Sample | J. of Portfolio Management | 2016 | 292 | T1p |
| 19 | `hlz2016` | …and the Cross-Section of Expected Returns | Review of Financial Studies | 2015/16 | 2,132 | T1 |
| 20 | `mcleanpontiff2016` | Does Academic Research Destroy Stock Return Predictability? | Journal of Finance | 2015/16 | 1,591 | T1 |
| 21 | `bailey2014` | Pseudo-Mathematics and Financial Charlatanism | Notices of the AMS | 2014 | 60† | T1 |
| 22 | `bailey2017` | The Probability of Backtest Overfitting | J. of Computational Finance | 2016/17 | — | T1 |
| 23 | `moreira2017` | Volatility-Managed Portfolios | Journal of Finance | 2017 | 573 | T1 |
| 24 | `gu2020` | Empirical Asset Pricing via Machine Learning | Review of Financial Studies | 2020 | 2,453 | T1 |
| 25 | `thorp2006` | The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market | Handbook of Asset and Liability Mgmt | 2006 | 159† | T3 |

Quality check: 22/25 peer-reviewed (88% ≥ 60% requirement); all entries verified to exist in at least one scholarly index with correct venue/authors; no fabricated references.

## 3. Annotated Bibliography

### Theme A — Momentum & Trend Following (core edge used by AQR, Man, Winton, CTAs)

**Jegadeesh & Titman (1993) `jegadeesh1993`** — *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*, JoF.
- Relevance: The founding paper of cross-sectional momentum — buy past 6–12m winners over ~3–12m holding periods. The single most implementable equity anomaly for daily-bar systems.
- Key findings: 12-month formation/3–6 month holding delivered ~1%/month risk-adjusted outperformance 1965–89 on NYSE/AMEX stocks; profits persist up to 12 months, then reverse.
- Methodology: portfolio sorts on past returns, zero-cost winner-minus-loser spreads, sub-period robustness.
- Contribution: defines the exact lookback/holding grid we can replicate with Alpaca daily bars.

**Jegadeesh (1990) `jegadeesh1990`** — *Evidence of Predictable Behavior of Security Returns*, JoF.
- Relevance: documents the *short-term* (weekly/monthly) reversal effect — the complement to momentum and the reason momentum uses a 12–1 skip-month convention.
- Key findings: first-month losers outperform winners (reversal); monthly autocorrelation structure in returns.
- Contribution: explains why we skip the most recent month in momentum ranks; basis for potential short-horizon mean-reversion sleeve.

**Moskowitz, Ooi & Pedersen (2012) `mop2012`** — *Time Series Momentum*, JFE.
- Relevance: AQR-authored; the academic frame for trend following across asset classes. Time-series (own-past-return) sign predicts future returns — long if past 12m return positive, else flat/short.
- Key findings: TSM persisted across 58 instruments over 25+ years; explains profitability of managed futures/CTAs.
- Methodology: per-instrument 1–12m lookback regressions, vol-scaled positions.
- Contribution: the cleanest "trend filter + vol targeting" recipe — maps directly onto a long-only equity implementation.

**Daniel & Moskowitz (2016) `daniel2016`** — *Momentum Crashes*, JFE.
- Relevance: the mandatory risk warning for Theme A — momentum occasionally crashes in rebound regimes (post-drawdown, high market volatility), with losses of 50–80% in weeks.
- Key findings: crash conditional on market state; dynamic momentum (vol-scaling + bear-market conditioning) roughly halves crash severity while preserving mean returns.
- Contribution: directly motivates our risk-engine gates (drawdown kill-switch, vol targeting) and a defensive momentum variant.

**Han, Yang & Zhou (2013) `hyz2013`** — *A New Anomaly: The Cross-Sectional Profitability of Technical Analysis*, JFQA.
- Relevance: formalizes moving-average signals into a cross-sectional "trend factor" — MA distances as predictive characteristics sorted into portfolios.
- Key findings: trend-factor portfolios earn significant alpha beyond momentum; robust subperiods.
- Contribution: gives an academically validated bridge from simple MA rules (our v1 indicators: SMA/EMA/Donchian) to a rankable factor.

**Brock, Lakonishok & LeBaron (1992) `brock1992`** — *Simple Technical Trading Rules…*, JoF.
- Relevance: the classic academic test of MA crossovers, trading-range breaks, support/resistance on DJIA 1897–1986.
- Key findings: buy signals earned above-average returns, sell signals below-average; consistent subperiods (though post-publication performance decay is a caveat per Theme F).
- Contribution: precedent that our existing SMA/Donchian machinery rests on documented signals.

**Hurst, Ooi & Pedersen (2017) `hurst2017`** — *Demystifying Managed Futures*, JOIM (AQR).
- Relevance: practitioner documentation of diversified trend-following (TSMOM) performance across markets and regimes, including crisis alpha.
- Contribution: regime-behavior map for a trend sleeve; validates vol-targeting conventions.

**Asness, Frazzini, Israel & Moskowitz (2014) `asness2014`** — *Fact, Fiction, and Momentum Investing*, JPM (AQR).
- Relevance: practitioner rebuttal paper — momentum works across size, geography, asset classes; survives transaction costs at sensible turnover; debunks "momentum is only small-cap/short-term" myths.
- Contribution: the closest thing to a quant-firm playbook note in the corpus; calibrates realistic turnover/cost expectations for daily-bar momentum.

### Theme B — Mean Reversion & Statistical Arbitrage (Renaissance/Two-Sigma-style relative value)

**Gatev, Goetzmann & Rouwenhorst (2006) `ggr2006`** — *Pairs Trading*, RFS.
- Relevance: canonical pairs-trading rule: form pairs by normalized-price distance, trade spread reversion when it exceeds 2σ.
- Key findings: 1962–2002 pairs earned ~conservative spreads with small risk; profits declined over time but remained; performance concentrated outside small-cap universes.
- Methodology: top-20-cousin matching within sectors, spread z-score entry/exit.
- Contribution: fully implementable from daily bars on a modest universe; our cointegration/distance variant needs only pandas/statsmodels.

**Avellaneda & Lee (2010) `avellaneda2010`** — *Statistical Arbitrage in the US Equities Market*, Quantitative Finance.
- Relevance: the modern stat-arb template: PCA residual factor model → mean-reverting residuals (Ornstein-Uhlenbeck) → trade z-scores with linear dollar-neutral portfolio, vol-scaled.
- Key findings: historically ~10–12% annualized Sharpe > 1 before decay; profits decayed ~50% post-2007 (crowding), still positive with tighter risk.
- Contribution: the most sophisticated strategy in scope for our framework — but implementation-heavy (PCA, OU estimation); candidate for Phase 6, not first vertical slice.

**Jegadeesh (1990) `jegadeesh1990`** (cross-listed) — short-horizon reversal basis.

### Theme C — Factor Investing (the "what quant funds own" layer)

**Fama & French (1993) `ff1993`** — *Common Risk Factors…*, JFE.
- Relevance: SMB/HML three-factor model — the root of all factor investing; defines value construction (book-to-market portfolios).
- Contribution: factor-model backdrop for attributing what our strategies actually earn (size/value/momentum exposure of our portfolio).

**Ang, Hodrick, Xing & Zhang (2006) `ang2006`** — *The Cross-Section of Volatility and Expected Returns*, JoF.
- Relevance: documents the low-volatility anomaly — high idiosyncratic-vol stocks *underperform* — the empirical foundation of low-vol/defensive equity portfolios (etf: USMV-style strategies).
- Contribution: a long-only-friendly defensive tilt implementable purely from return history (idiosyncratic vol from daily bars) — strong candidate given our long-only bias.

**Frazzini & Pedersen (2014) `bab2013`** — *Betting Against Beta*, JFE (AQR).
- Relevance: leveraged-constraint explanation of the low-beta anomaly; BAB factor (long low-beta, short high-beta) earned significant positive Sharpe across 19 asset classes.
- Contribution: second defensive tilt, computable from daily bars (rolling beta vs market) — long-only version = overweight low-beta names.

**Novy-Marx (2013) `novymarx2013`** — *The Other Side of Value: The Gross Profitability Premium*, JFE.
- Relevance: quality/gross-profitability factor; combines with value (the "quality minus junk" lineage).
- Data caveat: needs fundamentals — free sources exist but add a data dependency; hold for later.

**Asness, Moskowitz & Pedersen (2013) `amp2013`** — *Value and Momentum Everywhere*, JoF (AQR).
- Relevance: value and momentum are negatively correlated across every asset class; the 50/50 combo dominates either alone (Sharpe roughly doubles).
- Contribution: the core portfolio-design insight for us — blend a trend/momentum sleeve with a value or low-vol sleeve rather than running one signal.

### Theme D — Portfolio Construction (how the allocation actually gets sized)

**Markowitz (1952) `markowitz1952`** — *Portfolio Selection*, JoF.
- Relevance: mean-variance optimization — the foundation; estimation-error pathology is the practical lesson.
- Contribution: baseline; we deliberately prefer robust variants below.

**Maillard, Roncalli & Teïletche (2010) `maillard2010`** — *ERC Portfolios*, JPM.
- Relevance: equal risk contribution sits between equal-weight and min-variance; closed-form for long-only; robust to estimation error.
- Contribution: ideal position-sizing layer for multi-asset sleeves on a VM — deterministic, no expected-return estimates.

**López de Prado (2016) `lopezdeprado2016`** — *Building Diversified Portfolios that Outperform Out-of-Sample (HRP)*, JPM.
- Relevance: hierarchical risk parity — correlation clustering + recursive bisection allocation; out-of-sample variance reduction vs optimized portfolios.
- Contribution: implementable with scipy (linkage); upgrade path from ERC once our universe > ~10 names.

### Theme E — Risk Management & Position Sizing (the risk engine's academic spine)

**Moreira & Muir (2017) `moreira2017`** — *Volatility-Managed Portfolios*, JoF.
- Relevance: scaling factor exposure by (1/realized vol²) improves Sharpe and alphas across momentum, value, Fama-French factors; risk is *not* constant-proportional to premium.
- Contribution: the single highest-leverage overlay for us — vol-target every sleeve; also the academic justification for our drawdown kill-switch.

**Thorp (2006) `thorp2006`** — *The Kelly Criterion…*, Handbook of ALM.
- Relevance: fractional-Kelly position sizing for uncertain-edge settings; full Kelly is too volatile under estimation error (use ½ Kelly or less).
- Contribution: sizing philosophy for single-name allocations; bounded above by our risk engine caps regardless.

### Theme F — Methodology & Robustness (how to avoid fooling ourselves — mandatory reading)

**Harvey, Liu & Zhu (2016) `hlz2016`** — *…and the Cross-Section of Expected Returns*, RFS.
- Relevance: the "factor zoo" census — 400+ published factors; new factors need t > 3.0 to be believed after multiple-testing correction.
- Contribution: our default skepticism prior: treat any in-sample Sharpe from our own research as inflated until penalized.

**McLean & Pontiff (2016) `mcleanpontiff2016`** — *Does Academic Research Destroy Stock Return Predictability?*, JoF.
- Relevance: documented post-publication decay of ~32% (in-sample→post-sample) and ~58% (in-sample→post-publication) for published anomalies.
- Contribution: sets expectation haircuts for our backtest results; supports starting with the most-published, most-decayed-but-surviving families (momentum, low-vol) rather than niche factors.

**Bailey, Borwein, López de Prado & Zhu (2014 `bailey2014`, 2017 `bailey2017`)** — *Pseudo-Mathematics and Financial Charlatanism* (Notices AMS); *The Probability of Backtest Overfitting* (J. Computational Finance).
- Relevance: backtest overfitting formalized — PBO from combinatorially-split trials (CSCV); a Sharpe maximized over many configurations is likely noise.
- Contribution: mandates our methodology: trial-count bookkeeping, walk-forward + CSCV-style splits, deflated expectations. This is precisely the failure mode the v1 sweep/walk-forward tooling guards against.

**Gu, Kelly & Xiu (2020) `gu2020`** — *Empirical Asset Pricing via Machine Learning*, RFS.
- Relevance: the definitive comparison — trees/neural nets beat linear models on monthly equity returns (R²_oos ~0.4% monthly, ~2× linear), gains concentrated in nonlinear interactions.
- Contribution: capstone context: ML is an *upgrade path* after mechanical strategies are running; not the first vertical slice. Its methodology (OOS discipline, penalized models) informs our eventual ML phase.

## 4. Synthesis

*(Phase 3 output, produced by the deep-research synthesis_agent; canonical copy at [research/synthesis_report.md](research/synthesis_report.md). Reproduced below.)*

### 4.1 Literature Matrix

Legend: **S** = Supports, **C** = Contradicts, **—** = not addressed.

| Source (key) | Momentum/trend | Signal diversification | Vol/risk overlay | Portfolio construction | Decay skepticism | Daily-bar implementability | Method | Tier |
|---|---|---|---|---|---|---|---|---|
| markowitz1952 | — | — | — | C (naive use) | — | — | Theory | T1 |
| jegadeesh1990 | S (horizon boundary) | — | — | — | — | S | Quant | T1 |
| jegadeesh1993 | S | — | — | — | — | S | Quant sorts | T1 |
| brock1992 | S | — | — | — | C (post-pub.) | S | Quant | T1 |
| ff1993 | — | S (factor frame) | — | — | — | — | Quant | T1 |
| ang2006 | — | S (low-vol) | — | — | — | S | Quant sorts | T1 |
| ggr2006 | — | — | — | — | S (decay) | S | Quant | T1 |
| maillard2010 | — | — | S (sizing) | S | — | S | Theory+sim | T1p |
| avellaneda2010 | — | — | S (vol-scaled) | — | S (~50% decay) | C (PCA-heavy) | Quant | T1 |
| mop2012 | S | — | S (vol-target recipe) | — | — | S | Quant | T1 |
| amp2013 | S | S (neg. corr.) | — | — | — | — | Quant | T1 |
| bab2013 | — | S (low-beta) | — | — | — | S | Quant | T1 |
| novymarx2013 | — | S (quality) | — | — | — | C (needs fundamentals) | Quant | T1 |
| hyz2013 | S | — | — | — | — | S | Quant | T1 |
| hurst2017 | S | — | S | — | — | S | Practitioner | T1p/T2 |
| asness2014 | S | — | — | — | — | S (costs) | Practitioner | T1p |
| daniel2016 | C (crash) | — | S (dynamic mom.) | — | — | S | Quant | T1 |
| lopezdeprado2016 | — | — | — | S (vs MVO) | — | S | Sim | T1p |
| hlz2016 | — | — | — | — | S (t>3) | — | Econometrics | T1 |
| mcleanpontiff2016 | — | — | — | — | S (−58%) | — | Quant | T1 |
| bailey2014 | — | — | — | — | S (PBO) | S (methodology) | Theory | T1 |
| bailey2017 | — | — | — | — | S (CSCV) | S | Econometrics | T1 |
| moreira2017 | — | — | S | — | — | S | Quant | T1 |
| gu2020 | — | S (ML signal mix) | — | — | C (ML wins) | C (compute-heavy) | ML/Quant | T1 |
| thorp2006 | — | — | S (Kelly sizing) | — | — | S | Theory | T3 |

### 4.2 Key Themes

#### Theme 1: Momentum/trend is the most robust implementable edge — with documented crash conditions
**Evidence Strength: Strong** — 8 sources (6×T1, 2×T1p/T2)
**Sources:** `jegadeesh1993`, `mop2012`, `hyz2013`, `brock1992`, `asness2014`, `hurst2017`, `daniel2016`, `jegadeesh1990`

Three independent evidence streams converge on momentum as the best-supported daily-bar strategy family. Cross-sectional momentum (Jegadeesh & Titman, 1993) delivers ~1%/month on a 12-month-formation / 3–6-month-holding grid; time-series momentum (Moskowitz, Ooi & Pedersen, 2012) shows the same own-past-return predictability across 58 instruments and explains managed-futures profitability; and the trend factor (Han, Yang & Zhou, 2013) converts moving-average distances into a rankable characteristic with alpha beyond momentum — a direct academic license for our SMA/EMA/Donchian toolchain (precedent: Brock et al., 1992). Practitioner corroboration (Asness et al., 2014; Hurst, Ooi & Pedersen, 2017) establishes survival under transaction costs and regime breadth. The theme's boundary condition is equally well-documented: momentum crashes conditionally on market rebound after drawdowns with high volatility, with losses of 50–80% in weeks (Daniel & Moskowitz, 2016). The integrated reading is not "momentum works" but "momentum works conditionally on managing its rebound-state tail" — which is precisely what a risk-engine authority chain exists to enforce.

#### Theme 2: Signal diversification — value/low-vol/quality tilts are negatively correlated with momentum
**Evidence Strength: Moderate-Strong** — 5 sources (5×T1)
**Sources:** `amp2013`, `ang2006`, `bab2013`, `novymarx2013`, `ff1993`

The single most consequential portfolio-design fact in the corpus is that value and momentum are negatively correlated across every asset class, so a 50/50 blend roughly doubles Sharpe versus either sleeve alone (Asness, Moskowitz & Pedersen, 2013). For a long-only, daily-bar implementation, the natural complements are defensive: high idiosyncratic volatility predicts *under*performance (Ang et al., 2006) and low-beta portfolios earn higher risk-adjusted returns across 19 asset classes, explained by leverage constraints (Frazzini & Pedersen, 2014) — both computable purely from return history. Quality/profitability (Novy-Marx, 2013) completes the set but requires fundamentals data, a dependency the corpus flags but does not solve for us. Fama & French (1993) supplies the attribution frame: whatever we run, we should know our implicit size/value/momentum exposure. Synthesis: run momentum *with* a defensive tilt, not alone.

#### Theme 3: Vol targeting and risk-based sizing is the overlay that makes strategies implementable
**Evidence Strength: Moderate-Strong** — 5 sources (3×T1, 1×T1p, 1×T3)
**Sources:** `moreira2017`, `daniel2016`, `mop2012`, `hurst2017`, `thorp2006`

Volatility-managed portfolios — scaling exposure by inverse realized variance — improve Sharpe and alphas across momentum, value, and Fama-French factors, refuting the assumption that risk premium is proportional to risk at all times (Moreira & Muir, 2017). This is corroborated in practice: TSMOM's canonical recipe is vol-scaled positions (Moskowitz et al., 2012; Hurst et al., 2017), and Daniel & Moskowitz (2016) show dynamic (vol-scaled, bear-conditioned) momentum roughly halves crash severity while preserving mean returns. Thorp (2006) adds the sizing philosophy: fractional Kelly (½ Kelly or less) because edges are estimated with error, and always bounded by hard caps. The synthesis: vol targeting is not one strategy among many — it is the shared primitive that converts every raw signal in this corpus into a tolerable risk stream, and it is the academic justification for the drawdown kill-switch.

#### Theme 4: Portfolio construction robustness — ERC/HRP dominate naive mean-variance out-of-sample
**Evidence Strength: Moderate** — 3 sources (2×T1/T1p, plus markowitz1952 as baseline)
**Sources:** `markowitz1952`, `maillard2010`, `lopezdeprado2016`

Mean-variance optimization is optimal only when expected returns are known; in practice its weight estimates are dominated by estimation error. Equal risk contribution sits between equal-weight and min-variance, has closed-form long-only weights, and is robust to estimation error with no expected-return inputs (Maillard, Roncalli & Teïletche, 2010). Hierarchical risk parity adds correlation clustering via recursive bisection and reduces out-of-sample variance relative to optimized portfolios (López de Prado, 2016). The synthesis: Markowitz (1952) defines the objective, but the implementable answer for a small universe on a single VM is ERC first (deterministic, scipy-trivial), HRP as the upgrade path beyond ~10 names.

#### Theme 5: Predictability decay and the multiple-testing crisis are the governing skepticism
**Evidence Strength: Strong (methodological)** — 4 sources (4×T1)
**Sources:** `hlz2016`, `mcleanpontiff2016`, `bailey2014`, `bailey2017`

The robustness literature forms a coherent, mutually reinforcing discipline: 400+ published factors mean a new discovery needs t > 3.0 after multiple-testing correction to be believed (Harvey, Liu & Zhu, 2016); published anomalies decay ~32% out-of-sample and ~58% post-publication (McLean & Pontiff, 2016); and a Sharpe maximized over many trial configurations is likely noise — formalized as the probability of backtest overfitting via combinatorially-split cross-validation (Bailey et al., 2014; 2017). Integrated, these imply a haircut-first workflow: treat any in-sample Sharpe from our own sweeps as inflated until penalized by trial-count bookkeeping and walk-forward/CSCV-style validation. Strategically, McLean-Pontiff also implies picking the most-published, most-decayed-but-*surviving* families (momentum, low-vol) over niche factors — decay has already been priced by the market, and survivors are the durable ones.

#### Theme 6: The daily-bar implementability constraint separates adoptable from deferred strategies
**Evidence Strength: Emerging** — derived analytically from 6 sources; a synthesis construct, not a literature consensus
**Sources:** `ggr2006` (adoptable), `avellaneda2010` (deferred), `gu2020` (deferred), `novymarx2013` (deferred), `bailey2017` (methodology), `asness2014` (cost realism)

Reading the corpus against our constraints (daily bars, $100k paper capital, long-only bias, 1 free VM) produces a clear split rather than a ranking. Pairs trading via normalized-price distance with 2σ spread re-entry is fully implementable from daily bars on a modest universe (Gatev, Goetzmann & Rouwenhorst, 2006). By contrast, PCA/Ornstein-Uhlenbeck stat arb (Avellaneda & Lee, 2010) — which also showed ~50% post-2007 profit decay from crowding — and ML-based pricing (Gu, Kelly & Xiu, 2020, R²_oos ~0.4% monthly, ~2× linear, gains concentrated in nonlinear interactions) are upgrade paths, not first slices: the former for estimation complexity, the latter for compute and, critically, because flexible models are precisely the highest-risk class for backtest overfitting (Bailey et al., 2017). The corpus thus orders the roadmap: momentum/trend + defensive tilt + vol targeting + ERC sizing now; pairs next; stat arb and ML later under strict OOS discipline.

### 4.3 Contradictions & Resolutions

| # | Claim A | Claim B | Resolution |
|---|---|---|---|
| 1 | Short-term (monthly) losers outperform winners — reversal [`jegadeesh1990`] | Past 12m winners outperform over 3–12m holding [`jegadeesh1993`] | **Reconciled (horizon dependence).** Reversal dominates the most recent month; momentum dominates 12→3–6m. Non-contradiction once horizons are separated; jointly they produce the standard 12–1 skip-month convention. Both can coexist as distinct sleeves. |
| 2 | MA/trading-range rules earned significant returns 1897–1986 [`brock1992`] | Published signals decay ~58% post-publication [`mcleanpontiff2016`] | **Reconciled (temporal condition).** Brock's result is in-sample/pre-publication; McLean-Pontiff predicts (and documents) erosion after publication. Our MA/Donchian machinery is *precedent-licensed, not performance-promised*: apply the decay haircut to any Brock-style backtest. |
| 3 | Mean-variance portfolios are optimal [`markowitz1952`] | Optimized portfolios underperform out-of-sample due to estimation error; ERC/HRP more robust [`maillard2010`; `lopezdeprado2016`] | **Reconciled (theory vs implementation).** MVO is optimal under known parameters; the contradiction is an artifact of estimation error in inputs. ERC/HRP are the robust engineering answers; Markowitz supplies the objective, not the estimator. |
| 4 | Vol-managed scaling improves factor Sharpe, including momentum [`moreira2017`] | Momentum crashes conditionally in high-vol rebound states; vol-scaling alone roughly halves but does not eliminate crash severity [`daniel2016`] | **Mostly reconciled (conditional difference), residual flagged.** Both agree directionally — de-risk when realized vol is high. The residual disagreement is whether vol targeting *suffices*: Daniel-Moskowitz find bear-market conditioning adds protection beyond vol-scaling. Adopt both: vol target every sleeve AND a drawdown/bear-state gate. |
| 5 | ML models (trees/neural nets) beat linear models out-of-sample on monthly returns [`gu2020`] | Sharpe maximized over many configurations is likely noise; PBO formalizes overfitting [`bailey2014`; `bailey2017`] | **Reconciled (discipline condition).** Gu-Kelly-Xiu's gains are real but were obtained under strict OOS protocols — the same discipline Bailey et al. mandate. Flexible models are simultaneously the highest-reward and highest-overfit-risk class; ML adoption is gated on CSCV-grade validation, hence deferred. |

Cross-paper tension inventory (6 assessed pairs, `scholar_confirmation: pending` on all) and its coverage note are preserved in the canonical copy at [research/synthesis_report.md](research/synthesis_report.md) §3.

### 4.4 Knowledge Gaps

1. **Temporal gap — post-2020 regime unrepresented** (~23/25 sources pre-2020). The corpus predates zero-commission retail flow, 2020–2022 volatility cycles, and current crowding states. McLean-Pontiff decay estimates (−58% post-publication) may understate current decay for crowded signals. *Implication:* apply the published haircut plus an additional conservatism margin, and validate every adopted signal on 2020–2026 daily bars before trusting any backtest that ends earlier.
2. **Empirical gap — no evidence at our scale of capital and data feed.** All corpus studies use large liquid universes and zero-cost paper portfolios; none quantifies execution slippage, IEX free-feed depth, or borrow-free long-only frictions at ~$100k. Asness et al. (2014) asserts cost survival only at institutional turnover/cost assumptions. *Implication:* our paper-trading phase is a measurement instrument, not a formality — record realized vs backtest costs per sleeve.
3. **Methodological gap — overlay interactions unquantified.** No corpus paper tests the joint effect of stacking vol targeting + drawdown kill-switch + fractional-Kelly caps on the same strategy; each is validated in isolation (Moreira & Muir, 2017; Thorp, 2006). Stacked overlays plausibly reduce both tail risk *and* mean return, and the net effect is unknown. *Implication:* backtest the overlay stack itself as a configuration, with trial-count bookkeeping per Bailey et al. (2017).
4. **Empirical/data gap — fundamentals-dependent factors lack a verified free pipeline.** Quality/profitability (Novy-Marx, 2013) is documented as a premium but the corpus offers no free-data solution; the value leg of the value+momentum blend (Asness et al., 2013) inherits this dependency. *Implication:* the near-term defensive complement should be return-computable tilts (low-vol, BAB) rather than quality/value.

### 4.5 Evidence Convergence Map

```
Strong:     [==========] T1 Momentum/trend edge (8 sources, T1/T1p; incl. crash boundary)
Mod-Strong: [========  ] T2 Signal diversification/defensive tilts (5 sources, T1)
Mod-Strong: [========  ] T3 Vol targeting/risk sizing overlay (5 sources, T1/T1p/T3)
Moderate:   [======    ] T4 Robust portfolio construction (3 sources, T1/T1p)
Strong:     [==========] T5 Decay & multiple-testing skepticism (4 sources, all T1, methodological)
Emerging:   [===       ] T6 Daily-bar implementability split (6 sources; synthesis-derived)
Gap:        [          ] Post-2020 evidence; sub-$1M execution evidence; overlay interactions (0 sources)
```

### 4.6 Theoretical Integration

The corpus hangs together on three mechanisms. First, **efficient markets with frictions**: anomalies persist only where arbitrage is costly. The leverage-constraint story is the clearest — constrained investors bid up high-beta/high-vol stocks, producing the low-beta and low-vol premia (Frazzini & Pedersen, 2014; Ang et al., 2006); notably, vol targeting (Moreira & Muir, 2017) is the same mechanism operationalized: it is a disciplined way for an unconstrained investor to harvest the premium that leverage-constrained ones overpay for. Second, **behavioral under/overreaction**: short-horizon reversal reflects overreaction (Jegadeesh, 1990), 12-month momentum reflects delayed underreaction (Jegadeesh & Titman, 1993), and momentum crashes mark the moment the underreaction trade unwinds in a rebound as losers get bailed out (Daniel & Moskowitz, 2016) — the same psychology that creates the edge creates its tail. Third, **adaptive markets / information diffusion**: publication itself erodes edges (McLean & Pontiff, 2016; Harvey, Liu & Zhu, 2016; Gatev et al., 2006 document pairs-profit decline; Avellaneda & Lee, 2010 document crowding decay). The unified implication for implementation: favor edges anchored in *durable frictions* (leverage constraints, risk-aversion state-dependence) over those resting on statistical accident, and treat every published Sharpe as a pre-haircut upper bound.

### 4.7 Synthesis Limitations

- **Annotation-level corpus**: the synthesis relies on the verified annotated bibliography, not full-text re-reading; effect sizes and method details are as recorded in the annotations.
- **Seminal-anchored time skew**: ~23/25 sources pre-2020 (flagged as DISTRIBUTIONAL_SKEW_ADVISORY above); post-2020 regime evidence is absent by design, and its implications are inferred, not observed.
- **Source-cluster correlation**: five sources are AQR-authored (`mop2012`, `hurst2017`, `asness2014`, `amp2013`, `bab2013`); apparent convergence on momentum and vol targeting partly reflects one firm's research program and self-advocacy, inflating the independence of Theme 1/3 evidence.
- **No re-analysis**: no underlying data was re-run; all quantitative claims (e.g., −58% decay, ~1%/month momentum) are quoted from the bibliography, not independently verified.
- **Candidate-pair scoping**: the tension inventory is a recall-limited scoped scan (6 pairs assessed), not exhaustive pairwise detection; cross-neighborhood tensions may exist unlisted.
- **US-equity concentration** in the corpus matches our scope but means cross-asset validation of our choices (e.g., TSMOM's 58-instrument results) cannot be replicated in our own context.

---

## 5. Search Limitations

- Verification was metadata-level (existence, venue, year, citation counts) via OpenAlex/Semantic Scholar — abstracts were not re-read for every entry; annotations draw on established summaries of these canonical papers.
- Practitioner/"who actually uses this at firm X" claims rest on author affiliations (e.g., AQR-authored papers) and widely-documented practice, not on proprietary firm disclosures (which don't exist in public form).
- Grey literature excluded by design; recent (2021–2026) strategy papers under-covered (see time-skew advisory).

## 6. AI Disclosure

This literature scan was produced with AI-assisted research tooling (deep-research skill pipeline: systematic search, API-based source verification via OpenAlex/Semantic Scholar, and agent-based synthesis), orchestrated by ZCode on 2026-09-06. All 25 citations were independently verified against scholarly indexes before inclusion; no reference was fabricated. Quantitative claims are quoted from the annotated sources, not independently re-derived.
