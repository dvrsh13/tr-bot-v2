# BUILD_LOG — tr-bot-v2

Chronological record of the autonomous build: phases, decisions, failures, fixes.
**Overnight session:** 2026-09-06 (operator asleep; build constrained to no-new-services).
Times local (UTC+5:30-ish, machine local).

---

## Session ground rules

1. No new MCPs/plugins/accounts/services. Locally installed tooling only + the already-connected Alpaca MCP (read-only data use).
2. All dependencies isolated inside the project (uv-managed `.venv`); nothing global. See ISOLATION.md.
3. Everything deterministic + tested; carry over v1's proven patterns (risk-stamp authority chain, paper-only guard, fail-closed runner, no-lookahead).
4. Local git commits at milestones; push deferred until operator creates the repo (PUSH_CHECKLIST.md).

## Phase 0 — Scaffold

- Project: `trbot` package, `src/` layout, hatchling, Python 3.12 (uv-managed).
- Deps: pandas, numpy, scipy, pydantic 2.x, pyyaml, pyarrow, matplotlib, rich; dev: pytest, ruff.
- Design decisions locked:
  - **Authority chain** (ported from v1): strategies PROPOSE target weights → RiskEngine APPROVES via `RiskDecision` stamps → broker EXECUTES only stamped orders. Kill switch re-read before every order.
  - **Modes:** `SIMULATION` (offline default) and `PAPER` (Alpaca paper endpoint) only; config guard rejects LIVE/REAL/PRODUCTION and empty strings.
  - **No-lookahead contract:** signals computed on data ≤ t; fills at t+1 open; indicators shift(1).
  - **Cross-sectional core** (new vs v1): universe loader + ranker — unblocks S1/S3/S4/S5 from STRATEGY-SHORTLIST.md.
  - **Trial ledger** (methodology mandate from synthesis §Theme 5): every backtest configuration is logged with a global trial counter; PBO-lite (CSCV-style) estimates overfitting probability for sweeps.
  - **State store:** SQLite (local) with schema mirroring the planned Turso tables (docs/DB_SCHEMA.md).
  - **Symbol normalization:** `BRK.B` (Alpaca) ⇄ `BRK-B` (Yahoo) handled in universe loader with canonical internal form.

## Phase 1 — Core (config, indicators, data) — COMPLETE

- `config.py`: pydantic Settings, deep-merge YAML, mode guard (LIVE/REAL/PRODUCTION/empty all rejected),
  broker URL allowlist (only the two paper hosts pass), orders double-gate (`orders.enabled` AND `TRBOT_ORDERS_ENABLED`).
- `indicators.py`: sma/ema/rsi, realized_vol, rolling_total_return (skip-window = the 12-1 convention),
  idio_vol + rolling_beta (Ang 2006 / BAB inputs), ma_distance (Han-Yang-Zhou trend factor),
  cross_sectional_rank (NaN-preserving percentiles), max_drawdown. No-lookahead property tested by
  append-perturbation tests.
- `data/schema.py`: canonical standardization (case-insensitive columns — regression-tested after Yahoo's
  Capitalized columns broke the first fetch), 10 validation checks, `repair_envelope` for upstream
  float-epsilon artifacts (PFE had 2 rows).
- `data/providers.py`: SyntheticProvider (crc32-seeded regime-switching — v1's process-salted `hash()` lesson),
  Parquet/CSV providers, AlpacaBarsProvider (first-party live path; parses the dict-keyed-by-symbol bars payload —
  v1's Phase-8 bug fixed by design; ≤25 symbols/request free-tier guard).
- `data/universe.py`: canonical symbol normalization (`BRKB`), provider-specific spelling maps (BRK-B / BRK.B).
- 34-symbol core universe (`config/universe_us_core.csv`).

**Failure & fix:** standardizer's rename map was a no-op for capitalized column names (`{c.lower(): c.lower()}`) —
every Yahoo fetch failed with "missing columns". Fixed to case-insensitive matching + regression test. Same class
of bug as v1's live-fire discoveries — caught at first integration, not at the end.

## Phase 2 — Real data acquisition — COMPLETE

- Yahoo (yfinance 1.7, dev-only dep) → `data/cache/*.parquet`: **34/34 symbols, 1,930 bars each,
  2019-01-02 → 2026-09-04** — covers the 2020–2026 validation window the synthesis demanded (knowledge gap #1).
- All snapshots pass the 10-check validation; PFE envelope artifact repaired deterministically.
- Data is a research snapshot; the framework's runtime path is Alpaca-first (never scraped data).

## Phase 3 — Strategies, risk, execution — COMPLETE

- 5 strategies (`strategies/base.py`) mapped from STRATEGY-SHORTLIST: `xs_momentum` (12-1 top-N),
  `tsmom_vol` (TSMOM + vol scaling, bounded by max_names), `trend_factor` (MA-distance composite),
  `lowvol` (idio-vol, inverse-vol weights), `mom_def_blend` (offense 70 / defense 30 — Theme 2).
- `risk.py`: RiskEngine with ordered checks, RiskDecision stamps, persistent fail-safe KillSwitch
  (corrupt file = triggered; manual-only reset).
  - **Bug caught by tests:** `fillna(0)` before the finite check laundered NaN into silent zeros — v1's exact
    lesson, reintroduced and caught. Fixed: raw values checked first.
  - Added `risk.on_violation: reject|scale` — reject = live default (fail closed); scale = research-only
    cap-and-renormalize with audit stamp (tsmom proposed ~28 names vs max_positions=10 → rejected forever;
    now bounded by construction AND scalable in research).
- `portfolio.py` + `execution/sim_broker.py`: fills, cash math, realized PnL net of commissions,
  order diffing with noise floor, 10%-equity order cap chunking, slippage direction tested.

## Phase 4 — Backtest engine — COMPLETE

- `backtest/engine.py`: decide at t close (data ≤ t only) → fill at t+1 open → mark at close → HWM/drawdown check.
  Kill → force-close at next open (protective exits never blocked).
- **Kill policies:** `halt` (live semantics, permanent) vs `cooldown` (research: auto-resume after N days).
  **Design insight from testing:** on cooldown resume the HWM must reset to the de-risked equity, else the kill
  re-triggers the same day (kill-loop) — v1 had no answer for this because it only ever halted.
- **No-lookahead gold test:** future-perturbation temporal isolation — perturbing all bars after date D leaves
  equity/decisions/fills through D bit-identical.
- `backtest/metrics.py`: CAGR/vol/Sharpe/Sortino/Calmar/turnover/costs + benchmark.

## Phase 5 — Research tooling — COMPLETE

- `research/trial_ledger.py`: append-only JSONL, dataset fingerprints, config hashes (multiple-testing bookkeeping).
- `research/walkforward.py`: anchored folds with warmup-aware OOS windows; fails loudly on short folds (v1 lesson).
- `research/pbo.py`: CSCV combinatorial PBO (Bailey et al. 2017); sanity-tested (real skill ordering → low PBO,
  pure noise → high PBO).

## Phase 6 — State, live path, CLI — COMPLETE

- `state.py`: SQLite store (order claims w/ 7-day TTL, runs, equity snapshots, capped audit) — schema documented
  in docs/DB_SCHEMA.md and mirrored to the planned Turso tables.
- `execution/alpaca_paper.py`: stdlib REST, code-level allowlist, double-gated submission, injectable transport
  for mock tests; deterministic `client_order_id` (date+symbol+side, qty excluded — v1 churn convention).
- `runner.py`: one-cycle fail-closed runner (exit 2 creds / 4 data / 5 recon / 6 broker); kill switch checked
  BEFORE data fetch (halted bots must not spend API calls); read-only plan emission when gates closed.
- `cli.py` + `config/default.yaml` + `config/research_cooldown.yaml`: selftest, backtest (+plot),
  validate-data, walkforward, sweep (PBO), trials.
- CI workflow for post-push verification.

## Phase 7 — Real-data validation (results in REPORT.md) — COMPLETE

All five strategies on 34 real symbols × 7.5y, honest costs, kill overlay:
trend_factor Sharpe 1.15 / tsmom_vol 0.92 / **mom_def_blend 1.06 at lowest blend vol** / lowvol 0.76 / xs_momentum 0.64.
Walk-forward (cooldown): all three lead strategies positive in ALL four OOS folds (blend +172% OOS, Sharpe 1.17).
PBO sweep (top_n 3–15): PBO 0.44 moderate → the edge is robust to the parameter; tuning it is noise → default top_n=12, untuned.
Theme 2 (blend > components) and Theme 3 (vol targeting helps) from the synthesis confirmed in our own data.

**Failure found in first real runs:** every strategy entered right before COVID (warmup ends Feb 2020), the halt
kill fired, and books sat dead for 6.5 years — halt semantics make backtests measure entry timing, not strategy.
Led to the cooldown research policy + HWM-reset-on-resume design above.

## Phase 8 — Quality gates — COMPLETE

- **158 tests green** (unit + integration incl. adversarial: NaN gates, allowlist, double-gate, kill-switch
  persistence/corruption, future-perturbation, order caps, runner exit codes).
- **ruff clean, formatted** (line-length 120; S105/S310 false positives documented as per-file ignores).
- **Golden-file regression pin:** synthetic selftest equity curve pinned by final value + sha256 digest (tests/unit/test_regression.py).
- **Local git commits at milestones; push deferred** (PUSH_CHECKLIST.md).
- Isolation contract documented (ISOLATION.md): all deps in `.venv/`, no global installs, no secrets on disk,
  no processes left running, full disposal = two `rm -rf`.
