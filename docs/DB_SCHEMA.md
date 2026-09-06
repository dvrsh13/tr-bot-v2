# DB schema — SQLite (local) ⇄ Turso (cloud mirror)

The state store (`src/trbot/state.py`) uses SQLite locally. When the Oracle VM
goes live, the same schema is provisioned on Turso (libSQL) so the dashboard
reads cloud state while the VM keeps a local mirror. No Postgres features are
used; the schema is deliberately SQLite/libSQL-portable.

## Tables

```sql
-- Order idempotency (v1 convention: deterministic claim ids per (date, symbol, side);
-- qty excluded so at most one order chunk per (symbol, side, day))
CREATE TABLE order_claims (
    claim_id   TEXT PRIMARY KEY,
    symbol     TEXT NOT NULL,
    side       TEXT NOT NULL,          -- buy | sell
    trade_date TEXT NOT NULL,
    claimed_at TEXT NOT NULL,          -- ISO 8601 UTC
    expires_at TEXT NOT NULL           -- claimed_at + 7 days
);
CREATE INDEX idx_claims_date ON order_claims(trade_date);

-- Run bookkeeping (paper runner cycles)
CREATE TABLE runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    mode        TEXT NOT NULL,         -- SIMULATION | PAPER
    status      TEXT NOT NULL,         -- running | ok | planned | halted | failed
    exit_code   INTEGER,               -- 0 ok | 2 creds | 3 state | 4 data | 5 recon | 6 broker
    notes       TEXT
);

-- Equity snapshots for the dashboard (written per cycle)
CREATE TABLE equity_snapshots (
    ts             TEXT NOT NULL,
    equity         REAL NOT NULL,
    cash           REAL NOT NULL,
    positions_json TEXT NOT NULL       -- {"SYM": market_value, ...}
);

-- Capped audit trail (risk decisions, kill events, order submissions)
CREATE TABLE audit_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    event  TEXT NOT NULL,
    detail TEXT
);
```

## Dashboard read contract (Phase 4)

The Vercel dashboard reads ONLY (read-only Turso token):
- `equity_snapshots` (latest N) → equity curve, cash, positions
- `runs` (latest) → heartbeat / last cycle status
- `audit_log` (tail) → risk events, kill switch, order log

A stale `runs` timestamp (> 48h) renders as "bot heartbeat stale" — never fake data.

## Kill switch

`kill_switch.json` stays a **file on the VM** (fail-safe semantics, corrupt ⇒
triggered). Its state is mirrored into `audit_log` for dashboard visibility;
the dashboard can never reset it (no write path).
