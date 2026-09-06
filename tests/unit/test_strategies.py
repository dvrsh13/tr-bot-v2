"""Strategy tests: contract, determinism, NaN handling."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trbot.data.schema import to_wide
from trbot.strategies.base import (
    LowVol,
    MomentumDefenseBlend,
    StrategyInput,
    TrendFactor,
    TSMomentumVol,
    XSMomentum,
    build_strategy,
)


@pytest.fixture
def snap(synth_frames):
    wide_close = to_wide(synth_frames, "close")
    returns = wide_close.pct_change()
    market = (wide_close / wide_close.iloc[0]).mean(axis=1)
    return StrategyInput(close=wide_close, returns=returns, market_close=market)


def _assert_weight_row(row: pd.Series, snap, max_positions=None):
    assert row.index.equals(snap.close.columns) or len(row) <= len(snap.close.columns)
    assert (row.dropna() >= 0).all()
    assert row.dropna().sum() <= 1.0 + 1e-9
    if max_positions:
        assert (row > 1e-9).sum() <= max_positions


class TestRegistry:
    def test_build_known(self):
        s = build_strategy("xs_momentum", {"top_n": 3})
        assert isinstance(s, XSMomentum) and s.top_n == 3

    def test_build_unknown(self):
        with pytest.raises(ValueError, match="unknown strategy"):
            build_strategy("hft_scalper")

    @pytest.mark.parametrize("bad", [{"lookback": 10}, {"skip": 999}, {"top_n": 0}])
    def test_param_validation(self, bad):
        with pytest.raises(ValueError):
            build_strategy("xs_momentum", bad)


class TestXSMomentum:
    def test_row_shape_and_weights(self, snap):
        w = XSMomentum(top_n=4).target_weights(snap).iloc[-1]
        assert (w > 0).sum() == 4
        _assert_weight_row(w, snap, max_positions=4)
        assert w[w > 0].nunique() == 1  # equal weight 1/4

    def test_picks_highest_momentum(self, snap):
        w = XSMomentum(lookback=252, skip=21, top_n=3).target_weights(snap).iloc[-1]
        from trbot.indicators import rolling_total_return

        scores = rolling_total_return(snap.close, 252, 21).iloc[-1]
        top3 = scores.dropna().sort_values(ascending=False).index[:3]
        assert set(w[w > 0].index) == set(top3)

    def test_deterministic(self, snap):
        a = XSMomentum().target_weights(snap)
        b = XSMomentum().target_weights(snap)
        pd.testing.assert_frame_equal(a, b)

    def test_insufficient_history_gives_no_weights(self, snap):
        short = StrategyInput(
            close=snap.close.iloc[:100], returns=snap.returns.iloc[:100], market_close=snap.market_close.iloc[:100]
        )
        w = XSMomentum(lookback=252).target_weights(short).iloc[-1]
        assert (w.fillna(0) == 0).all()


class TestTSMomentumVol:
    def test_long_book_gross_capped(self, snap):
        w = TSMomentumVol().target_weights(snap).iloc[-1]
        _assert_weight_row(w, snap)
        assert w.sum() <= 1.0 + 1e-9

    def test_vol_scaling_varies(self, snap):
        """Among SELECTED names (strongest trends, bounded by max_names), lower
        realized vol must receive a larger weight via the vol scalar."""
        from trbot.indicators import realized_vol

        strat = TSMomentumVol(target_vol=0.15, max_names=8)
        w = strat.target_weights(snap).iloc[-1]
        selected = w.index[w > 1e-9]
        if len(selected) >= 2:
            vol = realized_vol(snap.returns, 60).iloc[-1].loc[selected]
            scalars = (0.15 / vol).clip(0.5, 1.5)
            if scalars.nunique() > 1:
                assert w.idxmax() == scalars.idxmax()  # biggest scalar -> biggest weight

    def test_all_bearish_goes_flat(self):
        idx = pd.bdate_range("2020-01-01", periods=300)
        down = pd.DataFrame({f"S{i}": np.linspace(100, 10, 300) for i in range(4)}, index=idx)
        snap = StrategyInput(close=down, returns=down.pct_change(), market_close=down.mean(axis=1))
        w = TSMomentumVol().target_weights(snap).iloc[-1]
        assert (w == 0).all()


class TestTrendFactor:
    def test_row_contract(self, snap):
        w = TrendFactor(top_n=5).target_weights(snap).iloc[-1]
        _assert_weight_row(w, snap, max_positions=5)


class TestLowVol:
    def test_picks_lowest_idio_vol(self, snap):
        w = LowVol(vol_window=252, top_n=3).target_weights(snap).iloc[-1]
        _assert_weight_row(w, snap, max_positions=3)
        from trbot.indicators import idio_vol

        iv = idio_vol(snap.returns, snap.market_close.pct_change(), 252).iloc[-1]
        lowest3 = set(iv.dropna().sort_values().index[:3])
        assert lowest3.issubset(set(w[w > 0].index))

    def test_inverse_vol_weighting(self, snap):
        w = LowVol(vol_window=252, top_n=2).target_weights(snap).iloc[-1]
        from trbot.indicators import idio_vol

        iv = idio_vol(snap.returns, snap.market_close.pct_change(), 252).iloc[-1]
        picked = w[w > 0].index
        if len(picked) == 2:
            inv = 1 / iv.loc[picked]
            expected = inv / inv.sum()
            for s in picked:
                assert w[s] == pytest.approx(expected[s], rel=1e-6)


class TestBlend:
    def test_gross_equals_one_minus_defense(self, snap):
        strat = MomentumDefenseBlend(top_n=5, defense_weight=0.3)
        w = strat.target_weights(snap).iloc[-1]
        assert w.sum() == pytest.approx(1.0, abs=1e-9)
        _assert_weight_row(w, snap)

    def test_defense_weight_zero_is_pure_offense(self, snap):
        w = MomentumDefenseBlend(top_n=5, defense_weight=0.0).target_weights(snap).iloc[-1]
        assert w.sum() == pytest.approx(1.0, abs=1e-9)
        assert (w > 0).sum() == 5

    def test_param_guard(self):
        with pytest.raises(ValueError, match="defense_weight"):
            MomentumDefenseBlend(defense_weight=0.9)
