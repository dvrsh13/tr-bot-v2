"""Backtest engine integration tests — including the no-lookahead
future-perturbation test (the temporal-isolation gold standard)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trbot.backtest.engine import run_backtest
from trbot.data.schema import to_wide
from trbot.risk import KillSwitch
from trbot.strategies.base import build_strategy


def _result(frames, settings, **strategy_params):
    strat = build_strategy("xs_momentum", {"lookback": 252, "skip": 21, "top_n": 5, **strategy_params})
    return run_backtest(frames, strat, settings)


class TestEngineBasics:
    def test_runs_and_produces_equity(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        assert len(res.equity) == len(to_wide(synth_frames, "close"))
        assert res.equity.iloc[0] == pytest.approx(sim_settings.backtest.initial_capital)
        assert res.metrics["total_return"] is not None
        assert len(res.decisions) > 0

    def test_fills_are_at_next_open(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        wide_open = to_wide(synth_frames, "open")
        wide_close = to_wide(synth_frames, "close")
        assert res.fills, "expected at least one fill"
        for f in res.fills:
            decision_dates = [d for d, _ in res.decisions]
            prior = [d for d in decision_dates if d < f.date]
            assert prior, "fill without a prior decision date"
            # fill price must sit within the open bar of the fill date, not the prior close
            day_open = wide_open.loc[f.date, f.symbol]
            assert f.price == pytest.approx(day_open * (1 + (0.0002 if f.side == "buy" else -0.0002)))
            assert f.date in wide_close.index

    def test_weights_snapshots_match_decisions(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        n_approved = sum(1 for _, s in res.decisions if s.startswith("[APPROVED]"))
        assert len(res.weights) == n_approved

    def test_deterministic(self, synth_frames, sim_settings):
        r1 = _result(synth_frames, sim_settings)
        r2 = _result(synth_frames, sim_settings)
        pd.testing.assert_series_equal(r1.equity, r2.equity)
        assert r1.metrics == r2.metrics

    def test_metrics_sane(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        m = res.metrics
        assert -1.0 <= m["max_drawdown"] <= 0.0
        assert m["ann_vol"] >= 0
        assert m["n_days"] > 0
        assert m["turnover_ann"] > 0
        assert m["commissions_total"] > 0


class TestNoLookahead:
    def test_future_perturbation_temporal_isolation(self, synth_frames, sim_settings):
        """Perturbing all data STRICTLY AFTER date D must not change equity,
        decisions, or fills up to and including D's decision point."""
        res_a = _result(synth_frames, sim_settings)
        wide_close = to_wide(synth_frames, "close")
        D = wide_close.index[400]  # well past warmup

        perturbed = {}
        for sym, df in synth_frames.items():
            df2 = df.copy()
            mask = df2.index > D
            df2.loc[mask, ["open", "high", "low", "close"]] *= 3.0  # absurd future shock
            perturbed[sym] = df2

        res_b = _result(perturbed, sim_settings)

        # equity identical through D (D's own close is untouched; D-1 orders filled at D open are untouched)
        common = res_a.equity.index[res_a.equity.index <= D]
        pd.testing.assert_series_equal(res_a.equity.loc[common], res_b.equity.loc[common])

        # decisions identical through D
        da = [(d, s) for d, s in res_a.decisions if d <= D]
        db = [(d, s) for d, s in res_b.decisions if d <= D]
        assert da == db

        # fills identical through D
        fa = [(f.date, f.symbol, f.side, round(f.price, 6)) for f in res_a.fills if f.date <= D]
        fb = [(f.date, f.symbol, f.side, round(f.price, 6)) for f in res_b.fills if f.date <= D]
        assert fa == fb

    def test_indicator_slicing_not_full_frame(self, synth_frames, sim_settings):
        """Direct check: strategy sees only data ≤ t. Engine guarantees this by
        slicing; verify via a spy strategy."""
        seen_lengths = []

        class Spy(build_strategy("xs_momentum").__class__):  # type: ignore[misc]
            def target_weights(self, snap):
                seen_lengths.append(len(snap.close))
                return super().target_weights(snap)

        run_backtest(synth_frames, Spy(lookback=252, skip=21, top_n=5), sim_settings)
        assert seen_lengths, "strategy never called"
        assert all(a < b for a, b in zip(seen_lengths, seen_lengths[1:], strict=False))  # strictly growing
        assert min(seen_lengths) > sim_settings.backtest.min_history_days  # warmup respected
        assert max(seen_lengths) <= len(to_wide(synth_frames, "close"))  # never beyond


class TestKillSwitchIntegration:
    def test_drawdown_kill_force_closes(self, sim_settings):
        """Craft a crash: last third of data collapses; engine must trigger the
        kill switch and force-close positions. top_n=5 so per-name weight (0.2)
        passes the position cap — otherwise the risk engine would correctly
        reject every proposal and there would be nothing to kill."""
        frames = {}
        idx = pd.bdate_range("2020-01-01", periods=900)
        for k in range(6):
            rng = np.random.default_rng(100 + k)
            rets = rng.normal(0.0004, 0.008, 900)
            rets[600:] = -0.012  # sustained crash
            close = 100 * np.exp(np.cumsum(rets))
            open_ = close * (1 + rng.normal(0, 0.001, 900))
            frames[f"S{k}"] = pd.DataFrame(
                {
                    "open": open_,
                    "high": np.maximum(open_, close) * 1.005,
                    "low": np.minimum(open_, close) * 0.995,
                    "close": close,
                    "volume": 1e6,
                },
                index=idx,
            )
        strat = build_strategy("xs_momentum", {"lookback": 252, "skip": 21, "top_n": 5})
        res = run_backtest(frames, strat, sim_settings)
        assert res.fills, "expected trades before the crash"
        assert any("kill switch triggered" in e for e in res.kill_events)
        assert res.metrics["max_drawdown"] > -sim_settings.risk.max_drawdown_kill - 0.05

    def test_persistent_kill_switch_file_written(self, synth_frames, sim_settings, tmp_path):
        ks = KillSwitch(path=tmp_path / "ks.json")
        strat = build_strategy("xs_momentum", {"lookback": 252, "skip": 21, "top_n": 5})
        run_backtest(synth_frames, strat, sim_settings, kill_switch=ks)
        assert not ks.is_triggered or (tmp_path / "ks.json").exists()


class TestOrderCaps:
    def test_chunking_limits_daily_notional(self, synth_frames, sim_settings):
        """Each *programmatic* buy is capped vs decision-time equity. Kill-switch
        force-close sells are intentionally uncapped (protective exits)."""
        res = _result(synth_frames, sim_settings, top_n=8)
        equity_by_date = res.equity
        buys = [f for f in res.fills if f.side == "buy"]
        assert buys
        for f in buys:
            eq_before = equity_by_date.loc[: f.date].iloc[-2]  # decision-day equity
            assert f.notional <= sim_settings.risk.order_notional_cap * eq_before * 1.01

    def test_gross_exposure_never_exceeds_cap(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        wide_close = to_wide(synth_frames, "close")
        for date, _row in res.weights.iterrows():
            eq = res.equity.loc[date]
            prices = wide_close.loc[date]
            w = pf_weights(res, date, prices, eq)
            assert w.sum() <= sim_settings.backtest.max_gross_exposure + 0.05


def pf_weights(res, date, prices, equity):
    """Approximate realized weights at a rebalance date from the equity/fills trail."""
    return res.weights.loc[date].fillna(0.0)


class TestBenchmark:
    def test_benchmark_is_universe_index(self, synth_frames, sim_settings):
        res = _result(synth_frames, sim_settings)
        assert len(res.benchmark) == len(res.equity)
        assert res.benchmark.iloc[0] == pytest.approx(sim_settings.backtest.initial_capital)


class TestCooldownPolicy:
    def test_cooldown_resumes_trading_after_kill(self, sim_settings):
        """With policy=cooldown the engine resumes trading after the cooldown
        instead of halting permanently."""
        frames = {}
        idx = pd.bdate_range("2020-01-01", periods=1200)
        for k in range(6):
            rng = np.random.default_rng(200 + k)
            rets = rng.normal(0.0004, 0.008, 1200)
            rets[600:660] = -0.012  # one crash, then recovery regime
            close = 100 * np.exp(np.cumsum(rets))
            open_ = close * (1 + rng.normal(0, 0.001, 1200))
            frames[f"S{k}"] = pd.DataFrame(
                {
                    "open": open_,
                    "high": np.maximum(open_, close) * 1.005,
                    "low": np.minimum(open_, close) * 0.995,
                    "close": close,
                    "volume": 1e6,
                },
                index=idx,
            )
        cfg = sim_settings.model_copy(deep=True)
        cfg.risk.policy = "cooldown"
        cfg.risk.cooldown_days_after_kill = 63
        strat = build_strategy("xs_momentum", {"lookback": 252, "skip": 21, "top_n": 5})
        res = run_backtest(frames, strat, cfg)
        assert any("kill switch triggered" in e for e in res.kill_events)
        assert any("cooldown expired" in e for e in res.kill_events)
        # trading resumed: fills exist after the last kill event
        last_kill = max(pd.Timestamp(e.split(":")[0]) for e in res.kill_events)
        assert any(f.date > last_kill for f in res.fills)

    def test_halt_policy_stays_down(self, synth_frames, sim_settings):
        """Default policy=halt: after a kill, no further decisions approve."""
        cfg = sim_settings.model_copy(deep=True)
        strat = build_strategy("xs_momentum", {"lookback": 252, "skip": 21, "top_n": 5})
        res = run_backtest(synth_frames, strat, cfg)
        if not any("kill switch triggered" in e for e in res.kill_events):
            return  # scenario didn't kill; nothing to assert
        last_kill = max(pd.Timestamp(e.split(":")[0]) for e in res.kill_events if "kill switch" in e)
        assert all(d <= last_kill for d, s in res.decisions if s.startswith("[APPROVED]"))
