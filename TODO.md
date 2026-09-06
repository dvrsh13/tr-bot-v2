# tr-bot-v2 — Task Tracker

## Now
- [ ] **User (morning):** push the repo → [PUSH_CHECKLIST.md](PUSH_CHECKLIST.md) (2 commands)
- [ ] **User:** create accounts (PLAN.md §4) — Oracle (region + PAYG decision), Alpaca paper keys, Turso, Telegram, Healthchecks.io
- [ ] **User:** answer open decisions in PLAN.md §7

## Next (after accounts)
- [ ] Phase 0→1: OCI CLI wiring + VM bootstrap script (hardened Ubuntu ARM)
- [ ] Phase 2 live-fire: read-only Alpaca cycles + one tiny paper order
- [ ] Phase 3: systemd timers, Telegram, Healthchecks; Alpaca-vs-Yahoo data parity check
- [ ] Phase 4: dashboard (separate task, reads Turso — contract in docs/DB_SCHEMA.md)
- [ ] Phase 5: hardening drills

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
