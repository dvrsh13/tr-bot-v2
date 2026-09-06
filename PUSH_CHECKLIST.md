# PUSH_CHECKLIST — repo health check

Repo is live at `dvrsh13/tr-bot-v2` and pushes work from this machine.
This file is now the 30-second health check + go-live order of operations.

## 1. Verify the build locally (30 seconds)

```bash
uv sync --all-extras          # recreates .venv from uv.lock exactly
uv run pytest tests/ -q       # 158 tests
uv run trbot selftest         # engine sanity, PASS expected
uv run trbot validate-data    # 34/34 symbols, 0 problems (needs data/cache)
uv run trbot backtest --config config/research_cooldown.yaml --strategy mom_def_blend
```

## 2. Then resume the live path (ORACLE-SETUP.md)

1. **Oracle Cloud** — home region decision + PAYG decision (PLAN.md §7)
2. **Turso** — `turso db create trbot-v2`; schema in `docs/DB_SCHEMA.md`; read-only token for Vercel
3. **Dashboard** — deploy per `ORACLE-SETUP.md` §7; install as PWA on the iPhone
4. **Alpaca (new account) paper keys** — env-only on the VM when it exists (never in the repo)
5. **Monitoring** — add `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` (read-only) as GitHub
   repo secrets; `heartbeat-monitor.yml` arms itself

## 4. First paper order protocol (unchanged from PLAN.md)

Orders stay double-gated off until you explicitly open BOTH gates:
`orders.enabled: true` in config AND `TRBOT_ORDERS_ENABLED=true` in the
environment. Recommended: several read-only cycles (`trbot` runner without
gates) reviewing the emitted order plans first.
