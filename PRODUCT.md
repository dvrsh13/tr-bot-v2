# PRODUCT.md — tr-bot-v2 dashboard

> Written by `/impeccable init` in unattended mode: inferred from the operator's
> explicit brief (PLAN.md, STRATEGY-RESEARCH.md, session directives). Assumptions
> labeled inline. The operator's brief is authoritative.

## Product truth

**What it is:** a personal, read-only control surface for `tr-bot-v2` — an
autonomous paper-trading bot that runs on a free-tier cloud VM and writes its
state to Turso. This dashboard is how the operator checks on it from anywhere,
almost always from an iPhone (installed as a PWA from the home screen).

**Who uses it:** exactly one person — the operator who built the bot. Not a
product for other users. No auth theatre, no onboarding, no marketing surface.

**The job, in the operator's words and brief:** check that the bot is alive,
see how the paper portfolio is doing, see what it did today, and notice when
something is wrong (kill switch, stale heartbeat, failed cycle). "Function
focused," a "good UI," usable one-handed on a phone.

**Frequency:** glanced a few times a week, intensively after deployments or
market shocks. Sessions are 15–60 seconds long. [Assumption: glance pattern
typical for a personal bot monitor; not stated in brief.]

**Hard facts this surface must always tell truthfully:**
- It is PAPER trading — a "PAPER" badge is always visible (v1 rule: never fake data).
- A stale heartbeat (> ~48h since last bot run) must read as "system stale",
  never as a blank or zero.
- Kill switch state, last cycle status, and the data's own timestamp are
  first-class content, not chrome.

**Data contract (real):** Turso tables `runs` (started_at, status, exit_code),
`equity_snapshots` (ts, equity, cash, positions_json), `audit_log` (ts, event,
detail). The dashboard reads with a read-only token. When credentials are
absent (local dev, first deploy), it renders a clearly-labeled DEMO dataset so
the surface is fully inspectable — the demo label is part of the design, not a
hidden fallback.

**Platform:** responsive web, mobile-first (390px primary), deployed on Vercel
against Next.js. PWA: installable on iOS home screen, standalone display,
safe-area aware, dark by default (checked at night and in sunlight).

**Constraints:** read-only. No write endpoints, no trade actions, no settings —
the operator configures the bot in the repo, not here.

## Audience world

The operator is a developer running a quant research hobby project grounded in
the academic factor literature (momentum, vol targeting, risk-engine discipline).
Their world: trading terminals (Bloomberg's density, TradingView's charts),
system monitoring tools (Grafana, uptime dashboards), and iOS dark-mode apps.
The cultural home is the **trading terminal / system-monitor hybrid**, not the
consumer fintech app: tabular truth, monospaced numbers, status dots, no
hand-holding.

## Mode

**Operate.** Scanability, status legibility, and honest state rendering outrank
expression. Brand lives in precise details (type setting of numbers, status
grammar, the PAPER badge).
