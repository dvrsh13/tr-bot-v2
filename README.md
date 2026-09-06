# tr-bot-v2 (`trbot`)

Paper-only algorithmic trading framework — free-tier deployable (Oracle Always Free VM + Alpaca paper + Turso + Vercel dashboard).

See [PLAN.md](PLAN.md) for architecture, [STRATEGY-RESEARCH.md](STRATEGY-RESEARCH.md) for the academic basis,
[STRATEGY-SHORTLIST.md](STRATEGY-SHORTLIST.md) for the implementable strategy list, [REPORT.md](REPORT.md) for the
real-data validation results, and [ISOLATION.md](ISOLATION.md) for the strict isolation/disposal contract.

**Safety contract:** only `SIMULATION` and `PAPER` modes exist. There is no live-trading code path — enforced in
config loading and tested adversarially. Order submission is double-gated (config flag AND environment variable).

## Quick start

```bash
uv sync --all-extras                 # isolated .venv from uv.lock (Python 3.12)
uv run pytest tests/ -q              # test suite
uv run trbot selftest                # engine sanity on synthetic data

# research runs on cached real data (data/cache/*.parquet):
uv run trbot validate-data
uv run trbot backtest --strategy xs_momentum --plot
uv run trbot backtest --config config/research_cooldown.yaml --strategy mom_def_blend
uv run trbot walkforward --config config/research_cooldown.yaml --strategy tsmom_vol --folds 4
uv run trbot sweep --config config/research_cooldown.yaml --strategy xs_momentum \
    --grid '{"top_n":[3,5,8,10,12,15]}'
uv run trbot trials                  # the multiple-testing ledger (Bailey et al. discipline)
```

## Layout

```
src/trbot/
  config.py        strict pydantic settings; paper-only mode guard; broker URL allowlist
  indicators.py    SMA/EMA/RSI/vol/beta/idio-vol/MA-distance — all backward-looking
  data/            providers (synthetic | csv | parquet | Alpaca REST), 10-check validation, universe
  strategies/      xs_momentum, tsmom_vol, trend_factor, lowvol, mom_def_blend (STRATEGY-SHORTLIST S1–S5)
  risk.py          RiskEngine (approve-stamp authority chain), persistent fail-safe kill switch
  portfolio.py     ledger: fills, positions, realized PnL net of costs
  execution/       sim broker (no-lookahead fills) + Alpaca paper adapter (double-gated)
  backtest/        engine (t: decide → t+1 open: fill) + metrics
  research/        walk-forward, trial ledger, CSCV/PBO (Bailey et al.)
  state.py         SQLite state store (schema mirrors Turso — docs/DB_SCHEMA.md)
  runner.py        paper runner: one fail-closed cycle (exit codes 0/2/4/5/6)
  cli.py           trbot CLI
```

## Dashboard (PWA, Vercel)

`dashboard/` — "The Quote Board": a read-only, mobile-first PWA (installable on
iPhone via Safari → Add to Home Screen). Reads the bot's state from Turso with a
read-only token; renders a clearly-labeled DEMO dataset when credentials are
absent. Deploy: `ORACLE-SETUP.md` §7 (vercel CLI or the `dashboard-deploy`
GitHub Action). Design system recorded in `dashboard/DESIGN.md`.

## Deployment (Oracle VM)

`ORACLE-SETUP.md` is the complete path from account signup (including failure
triage) to a running bot: VM provisioning, `deploy/bootstrap.sh` (idempotent),
systemd timers, Turso wiring, monitoring (GitHub-Actions dead-man switch), and
the disaster playbook.

## Data refresh

`uv run python scripts/fetch_yahoo.py` refreshes the research snapshot (Yahoo,
research-only — the live path is the first-party Alpaca provider). The framework
never depends on scraped data at runtime.
