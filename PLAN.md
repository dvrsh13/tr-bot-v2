# tr-bot-v2 — Master Plan

**Status:** Planning complete → awaiting account creation → build starts Phase 0
**Last updated:** 2026-09-06
**Goal:** Fully autonomous paper-trading bot running 100% on free web services, with a function-focused dashboard (separate task).

---

## 1. TL;DR architecture

**Oracle Cloud Always Free VM** (Ubuntu ARM) runs a Python bot that talks only **outbound** to the **Alpaca paper trading API** (existing account `PA30HK6GKPDP`, $100k). Bot state lives in **Turso** (free hosted SQLite); the dashboard (Next.js on Vercel Hobby) reads the same Turso DB — so the dashboard never depends on the VM being up and the VM never needs a public port. Notifications via **Telegram**; dead-man monitoring via **Healthchecks.io**. Total cost: **$0**.

```
┌────────────────────────────────────────────────┐
│  ORACLE ALWAYS FREE VM (Ubuntu 24.04, ARM)     │
│  2 OCPU / 12 GB RAM / 200 GB storage — $0      │
│                                                │
│  Bot (Python 3.12 + uv, ported v1 core):       │
│   strategies → risk engine → Alpaca paper      │
│   systemd timers (market-hours aware)          │
│   local SQLite mirror                          │
│                                                │
│  OUTBOUND-ONLY: zero open ports except SSH     │
└──────┬──────────┬──────────┬──────────┬────────┘
       │          │          │          │  (all HTTPS, outbound)
       ▼          ▼          ▼          ▼
   Alpaca      Turso      Telegram   Healthchecks.io
   Paper API   (state     (alerts)   (dead-man switch:
   + IEX data   DB)                   bot died? → email)
                   ▲
                   │ reads directly
        ┌──────────┴──────────┐
        │ DASHBOARD: Next.js  │
        │ + shadcn/ui on      │
        │ Vercel Hobby — $0   │
        └─────────────────────┘
```

## 2. Lessons from v1 (`tr-bot` / trading-lab) — carried as design rules

v1's engineering was strong (178 tests, no-lookahead discipline, risk-stamp authority chain, fail-closed runner). Failures were infrastructure-class:

1. **Render free KV is in-memory only** → state did not survive provider restarts. *v2 rule: durable free DB (Turso), never free-tier Redis for state.*
2. **Free scraped data breaks** (Stooq added JS proof-of-work mid-project; yfinance is unofficial and 429-prone). *v2 rule: first-party API data only (Alpaca IEX) + explicit fallback chain; no scraping as primary.*
3. **Console-only steps block AI-driven builds** (v1 dashboard stalled on Render GitHub App authorization). *v2 rule: every service provisionable via CLI/API (Turso CLI, Vercel CLI, OCI CLI).*
4. **Integration bugs surfaced late** (Phase 8 live-fire: bars dict-keyed-by-symbol; Redis ACL AUTH). *v2 rule: read-only live-fire smoke tests against Alpaca in week 1; one tiny paper order before Phase 3.*
5. **GitHub Actions cron is best-effort** (20–40 min delays common, multi-hour drift documented, 2,000 min/mo private-repo cap, schedules disabled after 60 days repo inactivity). *v2 rule: VM systemd timers own scheduling; Actions = CI only.*
6. **Keep from v1:** risk engine + kill switch (11 checks, persistent file, fail-safe), paper-endpoint allowlist in code, double-gated order submission, deterministic `client_order_id` idempotency, "never fake data" dashboard principle, no-lookahead contracts, golden-file regressions.

## 3. Final stack decisions

| Layer | Choice | Runner-up | Why |
|---|---|---|---|
| Hosting | **Oracle Cloud Always Free** (Ubuntu 24.04 ARM, 2 OCPU/12 GB) | Fly.io (no true free), Render (spins down) | Only real always-free always-on compute; 10 TB egress |
| Broker | **Alpaca paper** (existing account) | Binance testnet (crypto, later) | Free, realistic fills, API already proven in v1 |
| Market data | **Alpaca IEX** (200 req/min, 25 sym/req) | Massive/Polygon free (5 req/min, 2y EOD) as fallback | First-party, keyless setup via paper account |
| State DB | **Turso** (5 GB, 500M reads, 10M writes/mo) | Neon (0.5 GB); Supabase ruled out (7-day pause) | SQLite dialect matches VM mirror; no pause risk |
| Dashboard | **Next.js + shadcn/ui + Recharts on Vercel Hobby** | Cloudflare Pages | Reads Turso directly; renders even if VM is down |
| Scheduling | **systemd timers** on VM (market-hours aware, jittered) | GH Actions (CI only) | Actions cron is best-effort timing |
| Notifications | **Telegram bot** | Discord webhook | Free, reliable, easy bot API |
| Dead-man switch | **Healthchecks.io** free | UptimeRobot (dashboard monitor) | Silence → email if VM/bot dies |
| CI/CD | GitHub private repo + Actions (lint/test/audit); deploy via SSH or git-pull timer | — | Never as the primary scheduler |

## 4. Account checklist

| # | Service | Action | Keys to hand over |
|---|---|---|---|
| 1 | Oracle Cloud | Free Tier signup (**home region is permanent** — pick deliberately); consider immediate PAYG upgrade | VM created; OCI API signing key; SSH path |
| 2 | Alpaca | Regenerate **paper** API keys | Key ID + secret |
| 3 | Turso | GitHub signup; create DB `trbot-v2` | DB URL + auth token |
| 4 | Vercel | GitHub signup (can defer to Phase 4) | Token (later) |
| 5 | Telegram | @BotFather → new bot | Bot token + chat ID |
| 6 | Healthchecks.io | Create 1–2 checks | Ping URLs |
| 7 | GitHub | New **private** repo `tr-bot-v2` | PAT (repo scope) |

## 5. Build phases

1. **Phase 0 — Wiring:** repo scaffold, secrets plumbing, MCP/CLI setup (OCI, Turso, gh).
2. **Phase 1 — VM bootstrap:** hardened Ubuntu ARM (key-only SSH, ufw, fail2ban, unprivileged user, auto-updates), uv + Python 3.12, systemd layout. Idempotent script = disaster-recovery doc.
3. **Phase 2 — Port v1 core, live-fire early:** risk engine, kill switch, paper broker, indicators, strategies; state Redis→SQLite/Turso. Read-only Alpaca smoke test week 1; one tiny paper order.
4. **Phase 3 — Autonomy:** systemd timers, data pipeline (Alpaca → Massive fallback → last-good cache), Telegram, Healthchecks, idempotent order claims.
5. **Phase 4 — Dashboard:** Next.js on Vercel reading Turso. Data contract: equity curve, positions, orders, risk events, heartbeat, PAPER badge.
6. **Phase 5 — Hardening:** kill-switch drill, VM-rebuild drill, log rotation, backup verification, GH Actions fallback-runner doc.
7. **Phase 6 (optional, later):** intraday 5-min cycles, Alpaca websocket streaming, crypto module (Binance public data + testnet).

## 6. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Oracle reclaims idle VM | Low (bot cycles keep it busy) → zero with PAYG | Heartbeat + active cycles; PAYG upgrade; state in Turso; 30-min rebuild script |
| "Out of capacity" at VM creation | Medium (region-dependent) | Quieter home region, off-peak retries, retry script (hitrov/oci-arm-host-capacity), PAYG priority |
| Oracle changes free terms | Medium | Everything rebuildable from scripts; GH Actions fallback runner documented |
| Data provider breaks (Stooq redux) | Medium | First-party APIs + fallback chain + last-good cache + Telegram alert on degradation |
| Free DB pause/limits | Low (Turso: none) | Turso chosen specifically to avoid Supabase's 7-day inactivity pause |
| Secrets leak | — | Env-only, git-ignored, audit scanner in CI, paper-only endpoint allowlist in code |
| ARM arch surprises | Low | pandas/numpy/scipy ship aarch64 wheels; uv-managed Python |

## 7. Open decisions (user)

1. **Oracle PAYG upgrade** — recommended: yes (card charged $0 for Always-Free usage; kills idle-reclamation risk; fixes capacity access).
2. **Home region** — recommended: quieter region over low-latency India metro; 100–200 ms is irrelevant at daily/5-min cycles.
3. **Scope** — equities-only daily cycle first; intraday + crypto as Phase 6. (Recommended.)
4. **DB confirm** — Turso unless Postgres preferred (then Neon, not Supabase).
5. **Fresh repo** `tr-bot-v2` (port v1 code deliberately, don't fork).

## 8. Strategy research

See [STRATEGY-RESEARCH.md](STRATEGY-RESEARCH.md) (academic literature scan) and [STRATEGY-SHORTLIST.md](STRATEGY-SHORTLIST.md) (implementable candidates mapped to our framework).
