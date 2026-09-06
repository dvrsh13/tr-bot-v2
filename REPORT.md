# Validation Report — tr-bot-v2 strategy research on real market data

**Run:** 2026-09-06 (overnight autonomous build) · **Data:** 34 US large caps, daily bars 2019-01-02 → 2026-09-04 (1,930 bars/symbol, Yahoo auto-adjusted, snapshot in `data/cache/`)
**Engine:** no-lookahead (next-open fills), commission 1 bps + slippage 2 bps per side, order cap 10% of equity, monthly rebalance, risk engine with 10% drawdown kill (cooldown 63 trading days — research semantics), trial ledger enforced.
**Status:** infrastructure validation, **NOT performance claims.** Every number below carries the McLean-Pontiff haircut expectation (published anomalies decayed ~58% post-publication).

## Headline results (full sample 2019-2026)

| Strategy | CAGR | Ann vol | Sharpe | Max DD | Turnover/yr | Cost drag |
|---|---|---|---|---|---|---|
| xs_momentum (12-1, top 10) | +9.2% | 15.8% | 0.64 | -22.0% | 3.4 | $501 |
| tsmom_vol (TSMOM + vol target) | +13.9% | 15.4% | 0.92 | -18.2% | 3.8 | $629 |
| trend_factor (MA distance) | +18.6% | 16.0% | 1.15 | -20.8% | 5.0 | $883 |
| lowvol (idio-vol tilt) | +7.3% | 9.9% | 0.76 | -18.6% | 1.4 | $174 |
| **mom_def_blend (70/30)** | **+13.7%** | **12.9%** | **1.06** | -18.3% | 3.5 | $447 |

Key observations, mapped to the literature (STRATEGY-RESEARCH.md):

1. **Theme 2 confirmed in our own data:** the momentum+defense blend earns Sharpe 1.06 vs momentum-alone 0.64 at LOWER vol (12.9% vs 15.8%) — the negative-correlation blend effect (Asness-Moskowitz-Pedersen 2013) is real in our sample.
2. **Theme 3 confirmed:** vol-targeted TSMOM (0.92) beats untargeted-style momentum (0.64) with smaller drawdowns.
3. **Trend factor posts the highest Sharpe (1.15) at the highest turnover (5.0/yr)** — most exposed to cost/decay haircuts; treat as the most fragile of the winners (Theme 5).
4. All strategies hit the 10% kill switch multiple times (COVID Feb-2020, 2022 bear, 2024 vol events) — with halt semantics the sample ends there (the kill works); with 63-day cooldown the measured results above include re-entries.

## Walk-forward (4 anchored OOS folds, cooldown policy)

| Strategy | OOS total | OOS Sharpe | Folds positive | Worst fold DD |
|---|---|---|---|---|
| xs_momentum | +102.3% | 0.72 | 4/4 | -19.4% |
| tsmom_vol | +180.0% | 1.03 | 4/4 | -18.2% |
| mom_def_blend | +172.0% | 1.17 | 4/4 | -18.3% |

No single fold carries the result; every fold is OOS by construction (engine sees only prior history).

## Parameter robustness (PBO sweep)

Sweep of `top_n ∈ {3,5,8,10,12,15}` for xs_momentum: **PBO 0.44 (moderate, 70 CSCV splits)** — the in-sample-best configuration lands below the out-of-sample median 44% of the time. Translation: **the edge is robust to the parameter; tuning the parameter is noise.** Broader books (top 12-15, OOS Sharpe ≈ 1.0-1.1) beat concentrated ones (top 3-5, ≈ 0.7) — consistent with the breadth logic of the momentum literature. Decision: default top_n = 12, never tuned per-period.

## Known limitations / haircuts (read before trusting any number above)

1. **Post-publication decay:** these families are heavily published; McLean-Pontiff documents ~58% post-publication decay. Our Sharpe 0.6-1.2 in-sample-era numbers should be mentally halved at best.
2. **Data provenance:** Yahoo auto-adjusted bars (split+dividend) as a research snapshot. The live path is Alpaca IEX (first-party) — provider code exists and is tested; real-data parity check happens when paper credentials arrive. IEX's ~2-3% volume coverage makes its bars noisier than Yahoo's consolidated ones.
3. **Survivorship/selection bias:** the 34-symbol universe is today's mega caps — upward-biased. A point-in-time universe (e.g., index membership history) is required before trusting absolute returns. The strategy RANKING (blend > momentum alone) is more trustworthy than the levels.
4. **Costs are linear approximations** (fixed bps, no market impact) — fine at $100k paper scale in mega caps; conservative at 5x turnover for trend_factor.
5. **Cooldown kill semantics are a research choice.** Live operation halts permanently and pages a human. The cooldown results answer "what does the strategy do," not "what would the operator system do."
6. **Overlay interaction unquantified** (knowledge gap #3 from the synthesis): vol targeting + kill switch + caps stack — the PBO/walk-forward here measures the stack as-built, not each piece.

## Trial ledger

Every configuration run tonight is recorded in `state/trials.jsonl` (dataset fingerprinted). Current count: see `trbot trials`. The multiple-testing burden is real and tracked.

## What goes live first (recommendation)

1. **mom_def_blend** — best Sharpe/DD tradeoff, most diversified (Theme 2), moderate turnover.
2. **tsmom_vol** — simplest risk story, fully vol-targeted.
3. xs_momentum standalone — only as the offense sleeve of the blend.
4. trend_factor — watchlist: highest paper Sharpe but highest cost/decay exposure; revisit with real Alpaca IEX data before believing it.
