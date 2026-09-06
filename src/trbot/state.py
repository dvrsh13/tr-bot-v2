"""SQLite state store (local source of truth; schema mirrors the planned Turso
tables — see docs/DB_SCHEMA.md).

Holds: order idempotency claims, run bookkeeping, daily equity snapshots, and a
capped audit log. The kill switch lives in its own fail-safe file (risk.py) but
its state is mirrored here for the dashboard.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS order_claims (
    claim_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    exit_code INTEGER,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS equity_snapshots (
    ts TEXT NOT NULL,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    positions_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_claims_date ON order_claims(trade_date);
"""

CLAIM_TTL_DAYS = 7


class StateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ---- order idempotency -------------------------------------------------
    def claim_order(self, claim_id: str, symbol: str, side: str, trade_date: str) -> bool:
        """Atomically claim an order id. False = already claimed (duplicate)."""
        now = datetime.now(UTC)
        expires = now + timedelta(days=CLAIM_TTL_DAYS)
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO order_claims (claim_id, symbol, side, trade_date, claimed_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (claim_id, symbol, side, trade_date, now.isoformat(), expires.isoformat()),
        )
        return cur.rowcount == 1

    def active_claims(self, trade_date: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT claim_id, symbol, side, trade_date FROM order_claims WHERE trade_date = ?", (trade_date,)
        ).fetchall()
        return [{"claim_id": r[0], "symbol": r[1], "side": r[2], "trade_date": r[3]} for r in rows]

    # ---- runs ----------------------------------------------------------------
    def start_run(self, mode: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO runs (started_at, mode, status) VALUES (?, ?, 'running')",
            (datetime.now(UTC).isoformat(), mode),
        )
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, exit_code: int, notes: str = "") -> None:
        self._conn.execute(
            "UPDATE runs SET finished_at = ?, status = ?, exit_code = ?, notes = ? WHERE run_id = ?",
            (datetime.now(UTC).isoformat(), status, exit_code, notes, run_id),
        )

    # ---- equity / audit --------------------------------------------------------
    def record_equity(self, equity: float, cash: float, positions: dict[str, float]) -> None:
        self._conn.execute(
            "INSERT INTO equity_snapshots (ts, equity, cash, positions_json) VALUES (?, ?, ?, ?)",
            (datetime.now(UTC).isoformat(), equity, cash, json.dumps(positions)),
        )

    def audit(self, event: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO audit_log (ts, event, detail) VALUES (?, ?, ?)", (datetime.now(UTC).isoformat(), event, detail)
        )

    def last_equity(self) -> float | None:
        row = self._conn.execute("SELECT equity FROM equity_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
        return float(row[0]) if row else None

    def audit_tail(self, n: int = 50) -> list[dict]:
        rows = self._conn.execute("SELECT ts, event, detail FROM audit_log ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"ts": r[0], "event": r[1], "detail": r[2]} for r in rows]
