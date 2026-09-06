"""TursoStateStore tests against a scripted mock of the /v2/pipeline endpoint."""

from __future__ import annotations

import pytest

from trbot.state_turso import TursoStateStore


class FakeTurso:
    """Executes the subset of SQL our store uses against an in-memory sqlite."""

    def __init__(self):
        import sqlite3

        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        from trbot.state import _SCHEMA

        self.conn.executescript(_SCHEMA)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, url: str, body: dict | None, headers: dict[str, str]) -> dict:
        assert method == "POST" and url.endswith("/v2/pipeline")
        assert headers["Authorization"].startswith("Bearer ")
        results = []
        for req in body["requests"]:
            if req["type"] == "close":
                results.append({"type": "ok", "response": {}})
                continue
            sql = req["stmt"]["sql"]
            args = [a["value"] for a in req["stmt"].get("args", [])]
            self.calls.append(
                ("exec" if sql.lower().startswith(("insert", "update", "create", "delete")) else "query", sql[:40])
            )
            cur = self.conn.execute(sql, args)
            if cur.description:
                cols = [{"name": d[0]} for d in cur.description]
                rows = [[_enc(v) for v in row] for row in cur.fetchall()]
                results.append({"type": "ok", "response": {"result": {"cols": cols, "rows": rows}}})
            else:
                returning = "returning" in sql.lower()
                rows = [[_enc(r[0])] for r in cur.fetchall()] if returning else []
                results.append(
                    {
                        "type": "ok",
                        "response": {"result": {"cols": [{"name": "claim_id"}] if returning else [], "rows": rows}},
                    }
                )
        self.conn.commit()
        return {"results": results}


def _enc(v):
    if v is None:
        return {"type": "null", "value": None}
    if isinstance(v, int):
        return {"type": "integer", "value": v}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, bytes):
        return {"type": "blob", "value": v.hex()}
    return {"type": "text", "value": str(v)}


@pytest.fixture
def store():
    fake = FakeTurso()
    st = TursoStateStore(database_url="libsql://trbot-test-example.turso.io", auth_token="tok", transport=fake)
    return st


class TestTursoStore:
    def test_requires_credentials(self, monkeypatch):
        monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
        monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="missing Turso credentials"):
            TursoStateStore()

    def test_rejects_non_turso_url(self, monkeypatch):
        monkeypatch.setenv("TURSO_DATABASE_URL", "http://evil.example.com")
        monkeypatch.setenv("TURSO_AUTH_TOKEN", "t")
        with pytest.raises(RuntimeError, match="unexpected TURSO_DATABASE_URL"):
            TursoStateStore()

    def test_claim_order_idempotent(self, store):
        assert store.claim_order("c1", "AAPL", "buy", "2026-09-06") is True
        assert store.claim_order("c1", "AAPL", "buy", "2026-09-06") is False
        assert len(store.active_claims("2026-09-06")) == 1

    def test_run_and_equity_lifecycle(self, store):
        rid = store.start_run("PAPER")
        store.finish_run(rid, "ok", 0, "done")
        store.record_equity(101_250.5, 1_250.5, {"AAPL": 100_000.0})
        store.audit("risk_decision", "[APPROVED]")
        assert store.last_equity() == 101_250.5
        assert store.audit_tail(5)[0]["event"] == "risk_decision"
        lr = store.last_run()
        assert lr["status"] == "ok" and lr["exit_code"] == 0

    def test_last_equity_empty(self, store):
        assert store.last_equity() is None

    def test_pipeline_error_raises(self):
        def failing(method, url, body, headers):
            # schema DDL passes; any data query errors (simulates Turso outage)
            for req in body["requests"]:
                if req.get("stmt") and req["stmt"].get("sql", "").lower().startswith("select"):
                    return {"results": [{"type": "error", "error": {"message": "boom"}}]}
            return {
                "results": [{"type": "ok", "response": {"result": {"cols": [], "rows": []}}} for _ in body["requests"]]
            }

        st = TursoStateStore(database_url="libsql://x-y.turso.io", auth_token="t", transport=failing)
        with pytest.raises(RuntimeError, match="turso error"):
            st.last_equity()
