# Strategy Shortlist — Implementable Candidates Mapped to Our Framework

**Derived from:** [STRATEGY-RESEARCH.md](STRATEGY-RESEARCH.md) (25 verified papers + synthesis)
**Framework constraints:** daily OHLCV bars (Alpaca IEX free feed), US equities long-only bias, ~$100k paper capital, 1 free-tier VM, mandatory risk-engine authority chain, no-lookahead discipline.

---

## 1. Selection filter (from synthesis Themes 5 & 6)

A strategy enters the shortlist only if ALL hold:
1. **Daily-bar computable** — signal from OHLCV return history; no fundamentals, no tick data.
2. **Decay-resilient family** — heavily published, survived post-publication decay (McLean-Pontiff haircut applied in expectations).
3. **Long-only friendly** — expressible without shorting (our Alpaca paper account is long-only for equities simplicity).
4. **Risk-engine expressible** — position sizing and exposure boundable by v1's 11-check engine + kill switch.

## 2. Who uses what (the "quant firms & IBs" mapping)

| Strategy family | Academic anchor | Known practitioner usage |
|---|---|---|
| Cross-sectional momentum + factors | `jegadeesh1993`, `ff1993`, `amp2013` | AQR (pioneer), most factor shops, smart-beta ETF industry |
| Time-series momentum / trend | `mop2012`, `hurst2017` | CTAs & managed futures (Man AHL, Winton, AQR managed futures); Bridgewater-style trend systems |
| Pairs/stat-arb relative value | `ggr2006`, `avellaneda2010` | Renaissance-style stat arb (proprietary), pod shops (Citadel, Millennium, Point72 run momentum/stat-arb/pairs books) |
| Low-vol / low-beta defensive | `ang2006`, `bab2013` | AQR (BAB/defensive equity), low-vol ETF providers (USMV et al.) |
| Risk parity / ERC | `maillard2010` | Bridgewater (All Weather lineage), PanAgora, Robo-advisors |
| ML pricing | `gu2020` | Two Sigma, Renaissance-style shops (proprietary, compute-heavy) |
| Vol targeting / risk sizing | `moreira2017`, `thorp2006` | Near-universal overlay in vol-managed funds and CTAs |
| Execution algos (VWAP/TWAP/impact) | (out of scope — Alpaca fills simulated) | IB desk infrastructure (Goldman RCA, etc.) |

Investment-bank-specific strategy work is mostly **execution and structured products** rather than alpha — out of scope for a long-only paper bot; the alpha families above are where our literature maps.

## 3. The shortlist (ordered by implementation priority)

### S1 — Cross-Sectional Momentum "12–1" (`jegadeesh1993`) — **Priority 1**
- **Signal:** rank universe by total return months t−12…t−2 (skip last month per `jegadeesh1990`); hold top-N.
- **Universe:** 100–300 liquid US large caps (data budget: Alpaca 200 req/min, 25 sym/req → ~8 batched calls per daily refresh — comfortable).
- **Rebalance:** monthly-ish (weekly check, monthly trade), long-only top decile/quintile.
- **Fit:** v1 already has a `momentum` strategy stub but single-symbol — needs a **cross-sectional ranker** (new component).
- **Risk notes:** crash-conditioning gate (Daniel-Moskowitz): de-risk when market 12m return < 0 AND market vol elevated (`daniel2016`).

### S2 — Time-Series Momentum + Vol Targeting (`mop2012`, `moreira2017`) — **Priority 1**
- **Signal:** per-name 12m total return sign → in/out; position size scaled to target vol (e.g., 10% ann) using 60d realized vol.
- **Fit:** direct upgrade of v1's `sma_trend`/`regime_trend`; vol-targeting slot in the risk engine.
- **Why first:** the synthesis's "shared primitive" — every other sleeve reuses the vol-targeting overlay.

### S3 — Trend Factor / MA-Distance Characteristic (`hyz2013`, `brock1992`) — **Priority 2**
- **Signal:** MA(3,6,9,12)-month distance-to-price as ranked characteristic; cross-sectional sort.
- **Fit:** pure reuse of v1 indicators (SMA/EMA/Donchian) plus the cross-sectional ranker from S1; combines with S1 into a composite trend score.

### S4 — Low-Volatility Tilt (`ang2006`) — **Priority 2**
- **Signal:** rank by trailing idiosyncratic vol (vs market factor, 1y daily); underweight high-vol names.
- **Fit:** return-only data; the defensive complement to S1–S3 per Theme 2 (negative correlation with momentum).

### S5 — Betting-Against-Beta, long-only expression (`bab2013`) — **Priority 3**
- **Signal:** rolling 1y beta vs market; overweight low-beta names.
- **Fit:** same mechanics as S4 (beta vs idio-vol variant); fold into a composite "defensive score" with S4.

### S6 — Pairs Trading, distance rule (`ggr2006`) — **Priority 4 (Phase 6)**
- **Signal:** normalize prices, pair top-20 "cousins" by distance within sector, trade |z|>2 spread entries to reversion.
- **Fit:** daily-bar OK, pure pandas/statsmodels; needs sector labels (free via Alpaca metadata or static mapping) and a larger universe. Deferred: cross-sectional machinery must exist first.

### S7 — Portfolio construction ladder (`maillard2010`, `lopezdeprado2016`) — **cross-cutting**
- **v2.0:** equal-weight across sleeve selections (deterministic baseline).
- **v2.1:** ERC (inverse-vol closed form) — no expected-return estimates, robust (Theme 4).
- **v2.2:** HRP once universe > ~10 names (scipy linkage + recursive bisection).

### S8 — Risk overlays (mandatory, not optional) (`moreira2017`, `daniel2016`, `thorp2006`, risk engine)
- Vol-target every sleeve (1/realized-variance scaling, 10–15% ann target).
- Fractional Kelly cap (≤ ½ Kelly) on single-name concentration, bounded by risk-engine 10% order cap.
- Momentum-crash gate: bear-state + high-vol regime → cut momentum sleeve exposure.
- Drawdown kill-switch (v1 carry-over) = the `daniel2016` tail backstop.

### S9 — Backtest discipline (mandatory) (`bailey2014`, `bailey2017`, `hlz2016`, `mcleanpontiff2016`)
- Trial ledger: every configuration tried is logged (count → multiple-testing honesty).
- Walk-forward + CSCV-style combinatorial splits for the PBO estimate of any swept strategy.
- Expectation haircut: post-publication decay ~58% on published anomalies; validate all signals on 2020–2026 bars (knowledge gap #1).

## 4. Explicitly deferred / rejected

| Candidate | Paper | Reason |
|---|---|---|
| PCA/OU statistical arbitrage | `avellaneda2010` | Estimation-heavy (PCA, OU calibration), ~50% documented crowding decay; revisit in Phase 6 after pairs |
| ML pricing models | `gu2020` | Compute + highest backtest-overfit class; gated on CSCV-grade validation existing first |
| Quality / gross profitability | `novymarx2013` | Needs fundamentals — no verified free pipeline yet; revisit if a fundamentals source lands |
| HFT / market making / execution algos | — | Microstructure data unavailable free; out of scope by constraint |
| Full mean-variance optimization | `markowitz1952` | Estimation-error fragility (Theme 4); superseded by ERC/HRP |

## 5. Gap analysis → implementation TODOs

1. **Cross-sectional engine** (v1 was single-symbol): universe loader, ranking framework, turnover control. *(Blocks S1, S3, S4, S5.)*
2. **Vol-targeting overlay** in risk engine (S2/S8) — extends v1's `RiskEngine` with a sizing stamp.
3. **Trial ledger + CSCV/PBO tooling** (S9) — extends v1's research package (walk-forward exists; add combinatorial splits).
4. **2020–2026 validation harness** — every shortlisted signal must be re-validated on recent bars (knowledge gap #1) before going live on paper.
5. **Composite score design** — S1+S3 (momentum+trend) and S4+S5 (low-vol+low-beta) as blended sleeves per Theme 2; sleeve blend ratio = the one parameter worth sweeping (with trial ledger).

## 6. What "success" looks like for the strategy track

- 3–5 sleeves running on paper with vol-targeted, risk-stamped allocations;
- every sleeve has a walk-forward + PBO report with honest haircuts;
- realized paper costs logged per sleeve vs backtest assumptions (knowledge gap #2);
- dashboard shows per-sleeve attribution (which edge is earning what).
