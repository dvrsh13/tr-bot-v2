"""Turso (libSQL) state store — the cloud mirror the dashboard reads.

Pure-stdlib HTTP client against Turso's /v2/pipeline endpoint (no SDK, keeping
the dependency surface identical to the VM's stdlib-REST philosophy). Implements
the same operations as the local SQLite StateStore so the runner can take
either backend; the VM writes to BOTH (local mirror + cloud) when configured.

Transport is injectable for tests. Credentials come from the environment only:
``TURSO_DATABASE_URL`` and ``TURSO_AUTH_TOKEN``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from trbot.state import _SCHEMA, CLAIM_TTL_DAYS

TursoTransport = Callable[[str, str, dict | None, dict[str, str]], dict]


def _default_transport(method: str, url: str, body: dict | None, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(
        url, method=method, headers=headers, data=json.dumps(body).encode() if body is not None else None
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


class TursoStateStore:
    """Same public surface as StateStore (claim_order, start_run, finish_run,
    record_equity, audit, last_equity, audit_tail, active_claims, close)."""

    def __init__(
        self, database_url: str | None = None, auth_token: str | None = None, transport: TursoTransport | None = None
    ) -> None:
        self.url = (database_url or os.environ.get("TURSO_DATABASE_URL", "")).rstrip("/")
        self.token = auth_token or os.environ.get("TURSO_AUTH_TOKEN", "")
        if not self.url or not self.token:
            raise RuntimeError("missing Turso credentials: set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN")
        parsed = urlparse(self.url)
        if parsed.scheme not in ("https", "libsql") or not parsed.hostname:
            raise RuntimeError(f"unexpected TURSO_DATABASE_URL: {self.url!r}")
        self._api = f"https://{parsed.hostname}" if parsed.scheme == "libsql" else self.url
        self._transport = transport or _default_transport
        self._headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        self._local = sqlite3.connect(":memory:")
        self._local.executescript(_SCHEMA)  # schema reference only; DDL runs on Turso
        self.ensure_schema()

    # ---- pipeline plumbing ---------------------------------------------------
    def _pipeline(self, statements: list[tuple[str, list]]) -> list[dict]:
        body = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {"sql": sql, "args": [{"type": t, "value": v} for t, v in _typed_args(args)]},
                }
                for sql, args in statements
            ]
            + [{"type": "close", "stmt": None}]
        }
        resp = self._transport("POST", f"{self._api}/v2/pipeline", body, self._headers)
        results = resp.get("results", [])
        out = []
        for res in results:
            if res.get("type") == "error":
                raise RuntimeError(f"turso error: {res.get('error')}")
            out.append(res.get("response", {}))
        return out

    def _query(self, sql: str, args: list | None = None) -> list[dict[str, object]]:
        rows = self._pipeline([(sql, list(args or []))])[0].get("result", {})
        cols = [c["name"] for c in rows.get("cols", [])]
        return [{c: _unpack(v) for c, v in zip(cols, row, strict=False)}
                for row in rows.get("rows", [])]

    def _execute(self, sql: str, args: list | None = None) -> None:
        self._pipeline([(sql, list(args or []))])

    def ensure_schema(self) -> None:
        for stmt in _SCHEMA.split(";"):
            if stmt.strip():
                self._execute(stmt)

    # ---- same surface as StateStore -------------------------------------------
    def claim_order(self, claim_id: str, symbol: str, side: str, trade_date: str) -> bool:
        now = datetime.now(UTC)
        expires = now + timedelta(days=CLAIM_TTL_DAYS)
        cur = self._pipeline(
            [
                (
                    "INSERT INTO order_claims (claim_id, symbol, side, trade_date, claimed_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(claim_id) DO NOTHING RETURNING claim_id",
                    [claim_id, symbol, side, trade_date, now.isoformat(), expires.isoformat()],
                )
            ]
        )[0]
        return bool(cur.get("result", {}).get("rows"))

    def active_claims(self, trade_date: str) -> list[dict]:
        return self._query(
            "SELECT claim_id, symbol, side, trade_date FROM order_claims WHERE trade_date = ?", [trade_date]
        )

    def start_run(self, mode: str) -> int:
        now = datetime.now(UTC).isoformat()
        self._execute("INSERT INTO runs (started_at, mode, status) VALUES (?, ?, 'running')", [now, mode])
        row = self._query("SELECT last_insert_rowid() AS id")[0]
        return int(row["id"])

    def finish_run(self, run_id: int, status: str, exit_code: int, notes: str = "") -> None:
        self._execute(
            "UPDATE runs SET finished_at = ?, status = ?, exit_code = ?, notes = ? WHERE run_id = ?",
            [datetime.now(UTC).isoformat(), status, exit_code, notes, run_id],
        )

    def record_equity(self, equity: float, cash: float, positions: dict[str, float]) -> None:
        self._execute(
            "INSERT INTO equity_snapshots (ts, equity, cash, positions_json) VALUES (?, ?, ?, ?)",
            [datetime.now(UTC).isoformat(), equity, cash, json.dumps(positions)],
        )

    def audit(self, event: str, detail: str = "") -> None:
        self._execute(
            "INSERT INTO audit_log (ts, event, detail) VALUES (?, ?, ?)", [datetime.now(UTC).isoformat(), event, detail]
        )

    def last_equity(self) -> float | None:
        rows = self._query("SELECT equity FROM equity_snapshots ORDER BY ts DESC LIMIT 1")
        return float(rows[0]["equity"]) if rows else None

    def audit_tail(self, n: int = 50) -> list[dict]:
        return self._query("SELECT ts, event, detail FROM audit_log ORDER BY id DESC LIMIT ?", [n])

    def last_run(self) -> dict | None:
        rows = self._query(
            "SELECT run_id, started_at, finished_at, mode, status, exit_code, notes "
            "FROM runs ORDER BY run_id DESC LIMIT 1"
        )
        return rows[0] if rows else None

    def close(self) -> None:
        self._local.close()


def _typed_args(args: list) -> list[tuple[str, object]]:
    out = []
    for a in args:
        if a is None:
            out.append(("null", None))
        elif isinstance(a, bool):
            out.append(("integer", int(a)))
        elif isinstance(a, int):
            out.append(("integer", a))
        elif isinstance(a, float):
            out.append(("float", a))
        else:
            out.append(("text", str(a)))
    return out


def _unpack(v: dict) -> object:
    t = v.get("type")
    val = v.get("value")
    if t == "integer":
        return int(val)
    if t == "float":
        return float(val)
    if t == "null":
        return None
    return val
