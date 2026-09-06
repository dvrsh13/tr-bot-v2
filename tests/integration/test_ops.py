"""State store, Alpaca adapter (mocked transport), and runner fail-closed tests."""

from __future__ import annotations

import json
import urllib.request

import pytest

from trbot.config import Settings
from trbot.execution.alpaca_paper import (
    AlpacaError,
    AlpacaPaperBroker,
    make_order_claim_id,
)
from trbot.risk import KillSwitch
from trbot.runner import run_paper_cycle
from trbot.state import StateStore


class TestStateStore:
    def test_order_claim_atomic(self, tmp_path):
        st = StateStore(tmp_path / "s.db")
        assert st.claim_order("c1", "AAPL", "buy", "2026-09-06") is True
        assert st.claim_order("c1", "AAPL", "buy", "2026-09-06") is False  # duplicate
        assert len(st.active_claims("2026-09-06")) == 1
        st.close()

    def test_run_lifecycle(self, tmp_path):
        st = StateStore(tmp_path / "s.db")
        rid = st.start_run("PAPER")
        st.finish_run(rid, "ok", 0, "done")
        st.record_equity(101_500.0, 1_500.0, {"AAPL": 100_000.0})
        st.audit("test_event", "detail")
        assert st.last_equity() == 101_500.0
        tail = st.audit_tail(5)
        assert tail[0]["event"] == "test_event"
        st.close()

    def test_last_equity_empty(self, tmp_path):
        st = StateStore(tmp_path / "s.db")
        assert st.last_equity() is None
        st.close()


def _mock_transport(responses: dict[tuple[str, str], tuple[int, object]]):
    def transport(req: urllib.request.Request) -> tuple[int, bytes]:
        key = (req.get_method(), req.full_url.split("?")[0])
        if key not in responses:
            raise AlpacaError(f"mock has no response for {key}")
        status, payload = responses[key]
        return status, json.dumps(payload).encode()

    return transport


@pytest.fixture
def paper_settings(monkeypatch):
    monkeypatch.setenv("ALPACA_KEY_ID", "test-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret")
    return Settings.model_validate({"mode": "paper"})


class TestAlpacaAdapter:
    def test_account_roundtrip(self, paper_settings):
        resp = {
            ("GET", "https://paper-api.alpaca.markets/v2/account"): (
                200,
                {"account_number": "PA123", "equity": "100000"},
            )
        }
        broker = AlpacaPaperBroker(paper_settings, transport=_mock_transport(resp))
        assert broker.get_account()["account_number"] == "PA123"

    def test_allowlist_enforced(self, paper_settings):
        broker = AlpacaPaperBroker(paper_settings)
        with pytest.raises(AlpacaError, match="not in allowlist"):
            broker._request("GET", "/v2/wallets")  # not a real reachable endpoint

    def test_live_url_refused(self, paper_settings):
        broker = AlpacaPaperBroker(paper_settings)
        with pytest.raises(AlpacaError, match="refusing non-paper"):
            broker._request(
                "GET",
                "https://live-api.example.com/v2/account".replace("https://live-api.example.com", ""),
                base="https://live-api.example.com",
            )

    def test_submit_blocked_without_double_gate(self, paper_settings):
        """Config flag on but env off -> submission must refuse."""
        from trbot.config import Settings as S

        s = S.model_validate({"mode": "paper", "orders": {"enabled": True}})
        assert s.orders_actually_enabled is False
        broker = AlpacaPaperBroker(s)
        with pytest.raises(AlpacaError, match="double-gate"):
            broker.submit_order(symbol="AAPL", qty=1, side="buy", client_order_id="x")

    def test_submit_sends_body(self, paper_settings, monkeypatch):
        monkeypatch.setenv("TRBOT_ORDERS_ENABLED", "true")
        from trbot.config import Settings as S

        s = S.model_validate({"mode": "paper", "orders": {"enabled": True}})
        captured = {}

        def transport(req: urllib.request.Request) -> tuple[int, bytes]:
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode())
            return 200, json.dumps({"id": "order-1", "status": "new"}).encode()

        broker = AlpacaPaperBroker(s, transport=transport)
        out = broker.submit_order(symbol="AAPL", qty=3.5, side="buy", client_order_id="trbot-2026-09-06-aapl-buy")
        assert out["id"] == "order-1"
        assert captured["body"]["client_order_id"] == "trbot-2026-09-06-aapl-buy"
        assert captured["body"]["side"] == "buy"

    def test_missing_credentials_fail_closed(self, monkeypatch):
        monkeypatch.delenv("ALPACA_KEY_ID", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
        broker = AlpacaPaperBroker(Settings(mode="SIMULATION"))
        with pytest.raises(AlpacaError, match="missing credentials"):
            broker.get_account()

    def test_claim_id_deterministic(self):
        a = make_order_claim_id("2026-09-06", "AAPL", "buy")
        b = make_order_claim_id("2026-09-06", "AAPL", "buy")
        assert a == b and "trbot" in a


class TestRunnerFailClosed:
    def _store(self, tmp_path):
        return StateStore(tmp_path / "state.db")

    def test_missing_credentials_exit_2(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ALPACA_KEY_ID", raising=False)
        monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
        st = self._store(tmp_path)
        s = Settings.model_validate({"mode": "paper"})
        code, plan = run_paper_cycle(s, st)
        assert code == 2
        assert any("missing" in n for n in plan.notes)
        st.close()

    def test_bad_data_exit_4(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ALPACA_KEY_ID", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")

        class BoomProvider:
            def fetch_batch(self, symbols):
                raise RuntimeError("network down")

        import trbot.runner as runner_mod

        orig = runner_mod.AlpacaBarsProvider
        runner_mod.AlpacaBarsProvider = lambda *a, **k: BoomProvider()
        try:
            st = self._store(tmp_path)
            s = Settings.model_validate({"mode": "paper"})
            code, plan = run_paper_cycle(s, st)
            assert code == 4
            st.close()
        finally:
            runner_mod.AlpacaBarsProvider = orig

    def test_read_only_cycle_plans_without_submitting(self, tmp_path, monkeypatch):
        """Gates closed: full data + strategy cycle runs, plan emitted, zero orders."""
        monkeypatch.setenv("ALPACA_KEY_ID", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
        monkeypatch.delenv("TRBOT_ORDERS_ENABLED", raising=False)

        import pandas as pd

        from trbot.data.providers import SyntheticProvider

        class FakeProvider:
            """Returns synthetic frames keyed by whatever symbols are requested
            (alpaca spellings), so the runner's frame keys line up."""

            def __init__(self, *a, **k):
                self._end = pd.Timestamp("2026-09-04")

            def fetch_batch(self, symbols):
                return {s: SyntheticProvider(days=800, end=self._end).load([s])[s] for s in symbols}

        import trbot.runner as runner_mod

        orig = runner_mod.AlpacaBarsProvider
        runner_mod.AlpacaBarsProvider = lambda *a, **k: FakeProvider()
        try:
            st = self._store(tmp_path)
            s = Settings.model_validate(
                {
                    "mode": "paper",
                    "data": {
                        "universe_path": "config/universe_us_core.csv",
                        "synthetic_days": 800,
                        "synthetic_symbols": 12,
                    },
                    "backtest": {"max_position_weight": 0.25},  # top_n=5 -> 0.2/name, passes cap
                    "strategy": {"name": "xs_momentum", "params": {"top_n": 5}},
                }
            )
            code, plan = run_paper_cycle(s, st)
            assert code == 0
            assert plan.targets, "expected target weights in the plan"
            assert len(plan.orders) >= 1
            assert plan.submitted == []
            assert any("gated off" in n for n in plan.notes)
            st.close()
        finally:
            runner_mod.AlpacaBarsProvider = orig

    def test_kill_switch_halt_exit_0(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ALPACA_KEY_ID", "k")
        monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
        ks = KillSwitch(path=tmp_path / "ks.json")
        ks.trigger("test halt")
        st = self._store(tmp_path)
        s = Settings.model_validate({"mode": "paper"})
        code, plan = run_paper_cycle(s, st, kill_switch=ks)
        assert code == 0
        assert not plan.targets
        st.close()
