"""Research tooling tests: trial ledger, walk-forward, PBO."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trbot.research.pbo import cscv_pbo, pbo_from_configs
from trbot.research.trial_ledger import TrialLedger, config_hash, dataset_fingerprint
from trbot.research.walkforward import walk_forward


class TestTrialLedger:
    def test_record_and_count(self, tmp_path):
        led = TrialLedger(tmp_path / "trials.jsonl")
        assert led.count() == 0
        t1 = led.record(
            strategy="xs_momentum",
            params={"top_n": 5},
            dataset="abc123",
            metrics={"sharpe": 1.2345678, "total_return": 0.15},
        )
        t2 = led.record(strategy="xs_momentum", params={"top_n": 8}, dataset="abc123", metrics={"sharpe": 0.5})
        assert (t1, t2) == (1, 2) and led.count() == 2

    def test_roundtrip(self, tmp_path):
        led = TrialLedger(tmp_path / "trials.jsonl")
        led.record(strategy="s", params={"a": 1}, dataset="d", metrics={"sharpe": 1.0})
        entries = led.load()
        assert entries[0]["strategy"] == "s"
        assert entries[0]["metrics"]["sharpe"] == 1.0
        assert "recorded_at" in entries[0]

    def test_for_dataset_filter(self, tmp_path):
        led = TrialLedger(tmp_path / "trials.jsonl")
        led.record(strategy="s", params={}, dataset="d1", metrics={})
        led.record(strategy="s", params={}, dataset="d2", metrics={})
        assert len(led.for_dataset("d1")) == 1

    def test_fingerprint_deterministic_and_content_sensitive(self, synth_frames):
        f1 = dataset_fingerprint(synth_frames)
        f2 = dataset_fingerprint(synth_frames)
        assert f1 == f2
        perturbed = {k: (v.iloc[:-1] if k == "S00" else v) for k, v in synth_frames.items()}
        assert dataset_fingerprint(perturbed) != f1

    def test_config_hash_order_insensitive(self):
        assert config_hash("s", {"a": 1, "b": 2}) == config_hash("s", {"b": 2, "a": 1})
        assert config_hash("s", {"a": 1}) != config_hash("t", {"a": 1})


class TestWalkForward:
    def test_folds_and_aggregate(self, synth_frames, sim_settings):
        strat = build_strategy_helper(sim_settings)
        res = walk_forward(synth_frames, strat, sim_settings, n_folds=3, min_oos_days=100)
        assert len(res.folds) == 3
        for a, b in zip(res.folds, res.folds[1:], strict=False):
            assert a.end < b.start
        assert "oos_return_total" in res.aggregate
        assert "oos_sharpe" in res.aggregate
        assert isinstance(res.summary(), str)

    def test_short_data_fails_loudly(self, synth_frames, sim_settings):
        strat = build_strategy_helper(sim_settings)
        with pytest.raises(ValueError, match="too short"):
            walk_forward(synth_frames, strat, sim_settings, n_folds=10, min_oos_days=200)

    def test_deterministic(self, synth_frames, sim_settings):
        strat = build_strategy_helper(sim_settings)
        a = walk_forward(synth_frames, strat, sim_settings, n_folds=2, min_oos_days=150)
        b = walk_forward(synth_frames, strat, sim_settings, n_folds=2, min_oos_days=150)
        assert a.aggregate == b.aggregate


def build_strategy_helper(settings):
    from trbot.strategies.base import build_strategy

    return build_strategy(settings.strategy.name, settings.strategy.params)


class TestCSCVPBO:
    def _matrix(self, n_dates=400, seed=7):
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range("2024-01-01", periods=n_dates)
        true_skill = np.linspace(1.0, 0.0, 5)  # config 0 has real edge, 4 has none
        cols = {}
        for c in range(5):
            cols[f"cfg{c}"] = rng.normal(0.0002 * true_skill[c], 0.01, n_dates)
        return pd.DataFrame(cols, index=dates)

    def test_perfect_skill_low_pbo(self):
        res = cscv_pbo(self._matrix(seed=1), n_blocks=8)
        assert 0.0 <= res.pbo <= 1.0
        assert res.n_splits == 70  # C(8,4)
        assert res.pbo <= 0.3  # clear skill ordering -> low overfitting probability

    def test_pure_noise_high_pbo(self):
        rng = np.random.default_rng(9)
        n = 400
        cols = {f"cfg{c}": rng.normal(0, 0.01, n) for c in range(5)}
        res = cscv_pbo(pd.DataFrame(cols), n_blocks=8)
        assert res.pbo >= 0.4  # identical distributions -> IS-best ~ coin flip

    def test_rejects_degenerate_input(self):
        with pytest.raises(ValueError):
            cscv_pbo(pd.DataFrame({"a": [0.01, -0.01]}), n_blocks=8)
        with pytest.raises(ValueError):
            cscv_pbo(pd.DataFrame({"a": np.random.default_rng(1).normal(size=300)}), n_blocks=8)

    def test_pbo_from_configs_runs_engine(self, synth_frames, sim_settings):
        grid = [{"top_n": 3}, {"top_n": 5}, {"top_n": 8}]
        res = pbo_from_configs(synth_frames, "xs_momentum", grid, sim_settings, n_blocks=6)
        assert res.n_configs == 3
        assert 0.0 <= res.pbo <= 1.0
        assert len(res.per_config_oos_sharpe) == 3
