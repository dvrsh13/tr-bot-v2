# tr-bot-v2 — Task Tracker

## Now
- [x] Repo pushed (dvrsh13/tr-bot-v2)
- [x] Turso + Vercel + new Alpaca accounts created (keys stay env-side — never shared in chat)
- [ ] **User:** Oracle signup (blocked) → follow [ORACLE-SETUP.md](ORACLE-SETUP.md) §1 triage
- [ ] **User:** dashboard deploy → [ORACLE-SETUP.md](ORACLE-SETUP.md) §7 (2 paths: CLI or GH Action secrets)
- [ ] **User:** new Alpaca paper keys → set as env on the VM when it exists (`.env.example` is the inventory)

## Next (only Oracle blocks these)
- [ ] VM: run `deploy/bootstrap.sh` → paste secrets → enable `trbot-paper.timer` (ORACLE-SETUP.md §3-5)
- [ ] Live-fire: watch 3+ read-only cycles, then open the order double-gate (PLAN.md protocol)
- [ ] Turso dual-write on the VM + `trbot sync-state` backfill → dashboard goes live (§6)
- [ ] Monitoring on: add TURSO_* secrets to GitHub repo → heartbeat-monitor.yml arms itself (§8)

## Strategy track
- [x] Academic literature scan → [STRATEGY-RESEARCH.md](STRATEGY-RESEARCH.md) (25 papers, API-verified)
- [x] Synthesis → STRATEGY-RESEARCH.md §4 + [research/synthesis_report.md](research/synthesis_report.md)
- [x] Shortlist → [STRATEGY-SHORTLIST.md](STRATEGY-SHORTLIST.md)
- [x] **Framework built + tested overnight** (158 tests, golden pin, ruff clean)
- [x] Real-data validation → [REPORT.md](REPORT.md): blend/trend/tsmom lead; WF 4/4 folds positive; PBO 0.44
- [ ] Alpaca IEX data parity check (when paper keys exist) — revalidate REPORT.md numbers
- [ ] Point-in-time universe (kills survivorship bias in absolute returns — REPORT.md §limitations)
- [ ] Composite sleeve weight sweep (blend defense_weight 0→0.5) with trial ledger
- [ ] Pairs trading (S6, Phase 6) after cross-sectional sleeves are live

## Done
- [x] Infra research + plan (PLAN.md, INFRA-RESEARCH.md)
- [x] v1 lessons captured (PLAN.md §2)
- [x] agent-reach installed isolated (`~/agentreach-sandbox`, disposable via `rm -rf`)
- [x] Overnight build: framework + strategies + validation (see BUILD_LOG.md, ISOLATION.md)
