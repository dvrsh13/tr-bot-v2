# PUSH_CHECKLIST — morning after the overnight build

Everything below was built and verified locally with no external services. To
publish, the only step that was impossible overnight is creating the remote.

## 1. Create the repo and push

```bash
cd ~/Documents/tr-bot-v2
git remote add origin git@github.com:<you>/tr-bot-v2.git   # private repo
git push -u origin main
```

Local history: committed in milestones (see `git log --oneline`). Working tree
should be clean except gitignored runtime dirs (`data/cache/`, `state/`,
`reports/plots/` — rebuildable, never pushed).

CI (`.github/workflows/ci.yml`) runs ruff + pytest + selftest on push — verify
it goes green on GitHub.

## 2. Verify the build locally (30 seconds)

```bash
uv sync --all-extras          # recreates .venv from uv.lock exactly
uv run pytest tests/ -q       # 158 tests
uv run trbot selftest         # engine sanity, PASS expected
uv run trbot validate-data    # 34/34 symbols, 0 problems (needs data/cache)
uv run trbot backtest --config config/research_cooldown.yaml --strategy mom_def_blend
```

## 3. Then resume PLAN.md §4 (accounts for the live path)

1. **Oracle Cloud** — home region decision + PAYG decision (PLAN.md §7)
2. **Alpaca paper keys** — hand to the runner via env only (`ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`)
3. **Turso** — `turso db create trbot-v2`; schema in `docs/DB_SCHEMA.md`
4. Then Phase 1 (VM bootstrap) — the framework is already Phase-2-ready.

## 4. First paper order protocol (unchanged from PLAN.md)

Orders stay double-gated off until you explicitly open BOTH gates:
`orders.enabled: true` in config AND `TRBOT_ORDERS_ENABLED=true` in the
environment. Recommended: several read-only cycles (`trbot` runner without
gates) reviewing the emitted order plans first.
