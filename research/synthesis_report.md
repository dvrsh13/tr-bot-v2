# Synthesis Report — Academic Trading Strategies for Quant Firms & Investment Banks

**Phase 3 (Analysis) · Synthesis Agent · 2026-09-06**
**Corpus:** 25 verified sources in `STRATEGY-RESEARCH.md` (Themes A–F). Tiers: T1 = peer-reviewed journal, T1p = practitioner journal, T2 = preprint/working paper, T3 = handbook.

---

## 1. Literature Matrix

Legend: **S** = Supports, **C** = Contradicts, **—** = not addressed.

| Source (key) | T1 Momentum/trend | T2 Signal diversification | T3 Vol/risk overlay | T4 Portfolio construction | T5 Decay skepticism | T6 Daily-bar implementability | Method | Tier |
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

---

## 2. Key Themes

### Theme 1: Momentum/trend is the most robust implementable edge — with documented crash conditions
**Evidence Strength: Strong** — 8 sources (Levels: 6×T1, 2×T1p/T2)
**Sources:** `jegadeesh1993`, `mop2012`, `hyz2013`, `brock1992`, `asness2014`, `hurst2017`, `daniel2016`, `jegadeesh1990`

Three independent evidence streams converge on momentum as the best-supported daily-bar strategy family. Cross-sectional momentum (Jegadeesh & Titman, 1993 [`jegadeesh1993`]) delivers ~1%/month on a 12-month-formation / 3–6-month-holding grid; time-series momentum (Moskowitz, Ooi & Pedersen, 2012 [`mop2012`]) shows the same own-past-return predictability across 58 instruments and explains managed-futures profitability; and the trend factor (Han, Yang & Zhou, 2013 [`hyz2013`]) converts moving-average distances into a rankable characteristic with alpha beyond momentum — a direct academic license for our SMA/EMA/Donchian toolchain (precedent: Brock et al., 1992 [`brock1992`]). Practitioner corroboration (Asness et al., 2014 [`asness2014`]; Hurst, Ooi & Pedersen, 2017 [`hurst2017`]) establishes survival under transaction costs and regime breadth. The theme's boundary condition is equally well-documented: momentum crashes conditionally on market rebound after drawdowns with high volatility, with losses of 50–80% in weeks (Daniel & Moskowitz, 2016 [`daniel2016`]). The integrated reading is not "momentum works" but "momentum works conditionally on managing its rebound-state tail" — which is precisely what a risk-engine authority chain exists to enforce.

### Theme 2: Signal diversification — value/low-vol/quality tilts are negatively correlated with momentum
**Evidence Strength: Moderate-Strong** — 5 sources (5×T1)
**Sources:** `amp2013`, `ang2006`, `bab2013`, `novymarx2013`, `ff1993`

The single most consequential portfolio-design fact in the corpus is that value and momentum are negatively correlated across every asset class, so a 50/50 blend roughly doubles Sharpe versus either sleeve alone (Asness, Moskowitz & Pedersen, 2013 [`amp2013`]). For a long-only, daily-bar implementation, the natural complements are defensive: high idiosyncratic volatility predicts *under*performance (Ang et al., 2006 [`ang2006`]) and low-beta portfolios earn higher risk-adjusted returns across 19 asset classes, explained by leverage constraints (Frazzini & Pedersen, 2014 [`bab2013`]) — both computable purely from return history. Quality/profitability (Novy-Marx, 2013 [`novymarx2013`]) completes the set but requires fundamentals data, a dependency the corpus flags but does not solve for us. Fama & French (1993 [`ff1993`]) supplies the attribution frame: whatever we run, we should know our implicit size/value/momentum exposure. Synthesis: run momentum *with* a defensive tilt, not alone.

### Theme 3: Vol targeting and risk-based sizing is the overlay that makes strategies implementable
**Evidence Strength: Moderate-Strong** — 5 sources (3×T1, 1×T1p, 1×T3)
**Sources:** `moreira2017`, `daniel2016`, `mop2012`, `hurst2017`, `thorp2006`

Volatility-managed portfolios — scaling exposure by inverse realized variance — improve Sharpe and alphas across momentum, value, and Fama-French factors, refuting the assumption that risk premium is proportional to risk at all times (Moreira & Muir, 2017 [`moreira2017`]). This is corroborated in practice: TSMOM's canonical recipe is vol-scaled positions (Moskowitz et al., 2012 [`mop2012`]; Hurst et al., 2017 [`hurst2017`]), and Daniel & Moskowitz (2016 [`daniel2016`]) show dynamic (vol-scaled, bear-conditioned) momentum roughly halves crash severity while preserving mean returns. Thorp (2006 [`thorp2006`]) adds the sizing philosophy: fractional Kelly (½ Kelly or less) because edges are estimated with error, and always bounded by hard caps. The synthesis: vol targeting is not one strategy among many — it is the shared primitive that converts every raw signal in this corpus into a tolerable risk stream, and it is the academic justification for the drawdown kill-switch.

### Theme 4: Portfolio construction robustness — ERC/HRP dominate naive mean-variance out-of-sample
**Evidence Strength: Moderate** — 3 sources (1×T1, 1×T1p, plus markowitz1952 as baseline)
**Sources:** `markowitz1952`, `maillard2010`, `lopezdeprado2016`

Mean-variance optimization is optimal only when expected returns are known; in practice its weight estimates are dominated by estimation error. Equal risk contribution sits between equal-weight and min-variance, has closed-form long-only weights, and is robust to estimation error with no expected-return inputs (Maillard, Roncalli & Teïletche, 2010 [`maillard2010`]). Hierarchical risk parity adds correlation clustering via recursive bisection and reduces out-of-sample variance relative to optimized portfolios (López de Prado, 2016 [`lopezdeprado2016`]). The synthesis: Markowitz (1952 [`markowitz1952`]) defines the objective, but the implementable answer for a small universe on a single VM is ERC first (deterministic, scipy-trivial), HRP as the upgrade path beyond ~10 names.

### Theme 5: Predictability decay and the multiple-testing crisis are the governing skepticism
**Evidence Strength: Strong (methodological)** — 4 sources (4×T1)
**Sources:** `hlz2016`, `mcleanpontiff2016`, `bailey2014`, `bailey2017`

The robustness literature forms a coherent, mutually reinforcing discipline: 400+ published factors mean a new discovery needs t > 3.0 after multiple-testing correction to be believed (Harvey, Liu & Zhu, 2016 [`hlz2016`]); published anomalies decay ~32% out-of-sample and ~58% post-publication (McLean & Pontiff, 2016 [`mcleanpontiff2016`]); and a Sharpe maximized over many trial configurations is likely noise — formalized as the probability of backtest overfitting via combinatorially-split cross-validation (Bailey et al., 2014 [`bailey2014`]; 2017 [`bailey2017`]). Integrated, these imply a haircut-first workflow: treat any in-sample Sharpe from our own sweeps as inflated until penalized by trial-count bookkeeping and walk-forward/CSCV-style validation. Strategically, McLean-Pontiff also implies picking the most-published, most-decayed-but-*surviving* families (momentum, low-vol) over niche factors — decay has already been priced by the market, and survivors are the durable ones.

### Theme 6: The daily-bar implementability constraint separates adoptable from deferred strategies
**Evidence Strength: Emerging** — derived analytically from 6 sources; this is a synthesis construct, not a literature consensus
**Sources:** `ggr2006` (adoptable), `avellaneda2010` (deferred), `gu2020` (deferred), `novymarx2013` (deferred), `bailey2017` (methodology), `asness2014` (cost realism)

Reading the corpus against our constraints (daily bars, $100k paper capital, long-only bias, 1 free VM) produces a clear split rather than a ranking. Pairs trading via normalized-price distance with 2σ spread re-entry is fully implementable from daily bars on a modest universe (Gatev, Goetzmann & Rouwenhorst, 2006 [`ggr2006`]). By contrast, PCA/Ornstein-Uhlenbeck stat arb (Avellaneda & Lee, 2010 [`avellaneda2010`]) — which also showed ~50% post-2007 profit decay from crowding — and ML-based pricing (Gu, Kelly & Xiu, 2020 [`gu2020`], R²_oos ~0.4% monthly, ~2× linear, gains concentrated in nonlinear interactions) are upgrade paths, not first slices: the former for estimation complexity, the latter for compute and, critically, because flexible models are precisely the highest-risk class for backtest overfitting (Bailey et al., 2017 [`bailey2017`]). The corpus thus orders the roadmap: momentum/trend + defensive tilt + vol targeting + ERC sizing now; pairs next; stat arb and ML later under strict OOS discipline.

---

## 3. Contradictions & Resolutions

| # | Claim A | Claim B | Resolution |
|---|---|---|---|
| 1 | Short-term (monthly) losers outperform winners — reversal [`jegadeesh1990`] | Past 12m winners outperform over 3–12m holding [`jegadeesh1993`] | **Reconciled (horizon dependence).** Reversal dominates the most recent month; momentum dominates 12→3–6m. Non-contradiction once horizons are separated; jointly they produce the standard 12–1 skip-month convention. Both can coexist as distinct sleeves. |
| 2 | MA/trading-range rules earned significant returns 1897–1986 [`brock1992`] | Published signals decay ~58% post-publication [`mcleanpontiff2016`] | **Reconciled (temporal condition).** Brock's result is in-sample/pre-publication; McLean-Pontiff predicts (and documents) erosion after publication. Our MA/Donchian machinery is *precedent-licensed, not performance-promised*: apply the decay haircut to any Brock-style backtest. |
| 3 | Mean-variance portfolios are optimal [`markowitz1952`] | Optimized portfolios underperform out-of-sample due to estimation error; ERC/HRP more robust [`maillard2010`; `lopezdeprado2016`] | **Reconciled (theory vs implementation).** MVO is optimal under known parameters; the contradiction is an artifact of estimation error in inputs. ERC/HRP are the robust engineering answers; Markowitz supplies the objective, not the estimator. |
| 4 | Vol-managed scaling improves factor Sharpe, including momentum [`moreira2017`] | Momentum crashes conditionally in high-vol rebound states; vol-scaling alone roughly halves but does not eliminate crash severity [`daniel2016`] | **Mostly reconciled (conditional difference), residual flagged.** Both actually agree directionally — de-risk when realized vol is high. The residual disagreement is whether vol targeting *suffices*: Daniel-Moskowitz find bear-market conditioning adds protection beyond vol-scaling. Adopt both: vol target every sleeve AND a drawdown/bear-state gate. |
| 5 | ML models (trees/neural nets) beat linear models out-of-sample on monthly returns [`gu2020`] | Sharpe maximized over many configurations is likely noise; PBO formalizes overfitting [`bailey2014`; `bailey2017`] | **Reconciled (discipline condition).** Gu-Kelly-Xiu's gains are real but were obtained under strict OOS protocols — the same discipline Bailey et al. mandate. Flexible models are simultaneously the highest-reward and highest-overfit-risk class; ML adoption is gated on CSCV-grade validation, hence deferred. |

### Cross-Paper Tension Inventory (Step 3b)

```yaml
cross_paper_tensions:
  - pair_id: CP-001
    paper_a: "jegadeesh1990"
    paper_b: "jegadeesh1993"
    candidate_basis: "opposite finding direction"
    overlap_topic: "Whether past returns predict future returns positively or negatively"
    a_finding: "First-month losers outperform winners (short-horizon reversal)"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme B annotation (cross-listed from Theme A)"
    b_finding: "12m-formation winners outperform over 3-6m holding"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme A annotation"
    pair_assessment: "conditional_difference"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 1"
    scholar_confirmation: "pending"
  - pair_id: CP-002
    paper_a: "brock1992"
    paper_b: "mcleanpontiff2016"
    candidate_basis: "shared construct/outcome/measure"
    overlap_topic: "Post-publication profitability of documented trading signals"
    a_finding: "MA crossover / trading-range break signals earned significant returns in-sample (1897-1986)"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme A annotation"
    b_finding: "Published anomalies decay ~32% out-of-sample and ~58% post-publication"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme F annotation"
    pair_assessment: "conditional_difference"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 2"
    scholar_confirmation: "pending"
  - pair_id: CP-003
    paper_a: "markowitz1952"
    paper_b: "maillard2010"
    candidate_basis: "shared RQ subtopic"
    overlap_topic: "Optimal portfolio weighting under uncertainty"
    a_finding: "Mean-variance frontier is optimal"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme D annotation"
    b_finding: "ERC is robust to estimation error where MVO is fragile"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme D annotation"
    pair_assessment: "contradiction"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 3"
    scholar_confirmation: "pending"
  - pair_id: CP-004
    paper_a: "markowitz1952"
    paper_b: "lopezdeprado2016"
    candidate_basis: "shared RQ subtopic"
    overlap_topic: "Optimal portfolio weighting under uncertainty"
    a_finding: "Mean-variance frontier is optimal"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme D annotation"
    b_finding: "HRP reduces out-of-sample variance vs optimized portfolios"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme D annotation"
    pair_assessment: "contradiction"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 3"
    scholar_confirmation: "pending"
  - pair_id: CP-005
    paper_a: "moreira2017"
    paper_b: "daniel2016"
    candidate_basis: "shared construct/outcome/measure"
    overlap_topic: "Does conditioning on volatility improve momentum performance?"
    a_finding: "Vol-managed momentum earns higher Sharpe/alpha"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme E annotation"
    b_finding: "Momentum crashes occur in high-vol rebound states; vol-scaling halves but does not eliminate them"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme A annotation"
    pair_assessment: "conditional_difference"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 4"
    scholar_confirmation: "pending"
  - pair_id: CP-006
    paper_a: "gu2020"
    paper_b: "bailey2017"
    candidate_basis: "agent-noted cross-cluster"
    overlap_topic: "Reliability of out-of-sample gains from flexible predictive models"
    a_finding: "Trees/neural nets ~2x linear-model OOS R2 on monthly returns"
    a_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme F annotation"
    b_finding: "Backtests maximizing Sharpe over many trials are likely overfit (PBO/CSCV)"
    b_evidence_pointer: "STRATEGY-RESEARCH.md §3 Theme F annotation"
    pair_assessment: "contradiction"
    resolution_status: "resolved_in_synthesis"
    resolution_pointer: "Synthesis Report > Contradictions & Resolutions, row 5"
    scholar_confirmation: "pending"
```

**Coverage Note**: 25 papers in corpus (the PRISMA flow line in the input reports 24 — a count discrepancy noted in Limitations); 6 candidate pairs considered (bases: opposite finding direction, shared construct, shared RQ subtopic, agent-noted cross-cluster). This is a **scoped advisory scan, not complete pairwise contradiction detection** — cross-neighborhood pairs not surfaced here may exist and are not claimed absent. Bibliographic coupling was not computed in this session (annotation-level corpus, no reference lists) and its absence does not exclude any pair. Scholar confirms each `resolution_pointer` and may flag additional cross-pairs.

---

## 4. Knowledge Gaps

1. **Temporal gap — post-2020 regime unrepresented** (~23/25 sources pre-2020). The corpus predates zero-commission retail flow, 2020–2022 volatility cycles, and current crowding states. McLean-Pontiff decay estimates (−58% post-publication) may understate current decay for crowded signals. *Implication:* apply the published haircut plus an additional conservatism margin, and validate every adopted signal on 2020–2026 daily bars before trusting any backtest that ends earlier.
2. **Empirical gap — no evidence at our scale of capital and data feed.** All corpus studies use large liquid universes and zero-cost paper portfolios; none quantifies execution slippage, IEX free-feed depth, or borrow-free long-only frictions at ~$100k. Asness et al. (2014 [`asness2014`]) asserts cost survival only at institutional turnover/cost assumptions. *Implication:* our paper-trading phase is a measurement instrument, not a formality — record realized vs backtest costs per sleeve.
3. **Methodological gap — overlay interactions unquantified.** No corpus paper tests the joint effect of stacking vol targeting + drawdown kill-switch + fractional-Kelly caps on the same strategy; each is validated in isolation (Moreira & Muir, 2017 [`moreira2017`]; Thorp, 2006 [`thorp2006`]). Stacked overlays plausibly reduce both tail risk *and* mean return, and the net effect is unknown. *Implication:* backtest the overlay stack itself as a configuration, with trial-count bookkeeping per Bailey et al. (2017 [`bailey2017`]).
4. **Empirical/data gap — fundamentals-dependent factors lack a verified free pipeline.** Quality/profitability (Novy-Marx, 2013 [`novymarx2013`]) is documented as a premium but the corpus offers no free-data solution; the value leg of the value+momentum blend (Asness et al., 2013 [`amp2013`]) inherits this dependency. *Implication:* the near-term defensive complement should be return-computable tilts (low-vol [`ang2006`], BAB [`bab2013`]) rather than quality/value.

---

## 5. Evidence Convergence Map

```
Strong:    [==========] T1 Momentum/trend edge (8 sources, T1/T1p; incl. crash boundary)
Mod-Strong:[========  ] T2 Signal diversification/defensive tilts (5 sources, T1)
Mod-Strong:[========  ] T3 Vol targeting/risk sizing overlay (5 sources, T1/T1p/T3)
Moderate:  [======    ] T4 Robust portfolio construction (3 sources, T1/T1p)
Strong:    [==========] T5 Decay & multiple-testing skepticism (4 sources, all T1, methodological)
Emerging:  [===       ] T6 Daily-bar implementability split (6 sources; synthesis-derived)
Gap:       [          ] Post-2020 evidence; sub-$1M execution evidence; overlay interactions (0 sources)
```

---

## 6. Theoretical Integration

The corpus hangs together on three mechanisms. First, **efficient markets with frictions**: anomalies persist only where arbitrage is costly. The leverage-constraint story is the clearest — constrained investors bid up high-beta/high-vol stocks, producing the low-beta and low-vol premia (Frazzini & Pedersen, 2014 [`bab2013`]; Ang et al., 2006 [`ang2006`]); notably, vol targeting (Moreira & Muir, 2017 [`moreira2017`]) is the same mechanism operationalized: it is a disciplined way for an unconstrained investor to harvest the premium that leverage-constrained ones overpay for. Second, **behavioral under/overreaction**: short-horizon reversal reflects overreaction (Jegadeesh, 1990 [`jegadeesh1990`]), 12-month momentum reflects delayed underreaction (Jegadeesh & Titman, 1993 [`jegadeesh1993`]), and momentum crashes mark the moment the underreaction trade unwinds in a rebound as losers get bailed out (Daniel & Moskowitz, 2016 [`daniel2016`]) — the same psychology that creates the edge creates its tail. Third, **adaptive markets / information diffusion**: publication itself erodes edges (McLean & Pontiff, 2016 [`mcleanpontiff2016`]; Harvey, Liu & Zhu, 2016 [`hlz2016`]; Gatev et al., 2006 [`ggr2006`] document pairs-profit decline; Avellaneda & Lee, 2010 [`avellaneda2010`] document crowding decay). The unified implication for implementation: favor edges anchored in *durable frictions* (leverage constraints, risk-aversion state-dependence) over those resting on statistical accident, and treat every published Sharpe as a pre-haircut upper bound.

---

## 7. Synthesis Limitations

- **Annotation-level corpus**: the synthesis relies on the verified annotated bibliography, not full-text re-reading; effect sizes and method details are as recorded in the annotations.
- **Seminal-anchored time skew**: ~23/25 sources pre-2020 (flagged upstream as DISTRIBUTIONAL_SKEW_ADVISORY); post-2020 regime evidence is absent by design, and its implications are inferred, not observed.
- **Source-cluster correlation**: five sources are AQR-authored ([`mop2012`], [`hurst2017`], [`asness2014`], [`amp2013`], [`bab2013`]); apparent convergence on momentum and vol targeting partly reflects one firm's research program and self-advocacy, inflating the independence of Theme 1/3 evidence.
- **Count discrepancy in input**: the PRISMA flow line reports 24 verified/included papers while the verification matrix lists 25 rows; this synthesis maps the 25 matrix rows.
- **No re-analysis**: no underlying data was re-run; all quantitative claims (e.g., −58% decay, ~1%/month momentum) are quoted from the bibliography, not independently verified.
- **Candidate-pair scoping**: the tension inventory is a recall-limited scoped scan (6 pairs assessed), not exhaustive pairwise detection; cross-neighborhood tensions may exist unlisted.
- **US-equity concentration** in the corpus matches our scope but means cross-asset validation of our choices (e.g., TSMOM's 58-instrument results) cannot be replicated in our own context.
