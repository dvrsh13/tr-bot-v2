"""Indicator tests incl. no-lookahead properties."""

import numpy as np
import pandas as pd
import pytest

from trbot.indicators import (
    cross_sectional_rank,
    ema,
    idio_vol,
    ma_distance,
    max_drawdown,
    realized_vol,
    rolling_beta,
    rolling_total_return,
    rsi,
    sma,
)


@pytest.fixture
def close():
    idx = pd.bdate_range("2020-01-01", periods=500)
    rng = np.random.default_rng(42)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, 500))), index=idx)


class TestNoLookahead:
    """Indicators must be backward-looking: appending future data must not
    change values at past timestamps."""

    def test_sma_past_values_stable_under_append(self, close):
        full = sma(close, 20)
        partial = sma(close.iloc[:300], 20)
        pd.testing.assert_series_equal(full.iloc[:300], partial)

    @pytest.mark.parametrize("fn", [sma, ema])
    def test_ma_past_stable(self, close, fn):
        full = fn(close, 50)
        partial = fn(close.iloc[:200], 50)
        pd.testing.assert_series_equal(full.iloc[:200], partial)

    def test_rsi_past_stable(self, close):
        full = rsi(close, 14)
        partial = rsi(close.iloc[:250], 14)
        pd.testing.assert_series_equal(full.iloc[:250], partial)

    def test_total_return_past_stable(self, close):
        full = rolling_total_return(close, 252, skip=21)
        partial = rolling_total_return(close.iloc[:400], 252, skip=21)
        pd.testing.assert_series_equal(full.iloc[:400], partial)


class TestRollingTotalReturn:
    def test_12_1_convention(self):
        idx = pd.bdate_range("2020-01-01", periods=300)
        s = pd.Series(np.linspace(100, 200, 300), index=idx)  # constant drift
        r = rolling_total_return(s, 252, skip=21)
        s.iloc[278] / s.iloc[27] - 1  # t-21 vs t-21-231... check endpoints
        # At position 278 (t), value uses close.shift(21)=s[257] over shift(252)=s[26]
        assert r.iloc[278] == pytest.approx(s.iloc[257] / s.iloc[26] - 1)

    def test_nan_before_lookback(self):
        s = pd.Series(np.ones(300), index=pd.bdate_range("2020-01-01", periods=300))
        r = rolling_total_return(s, 252, skip=21)
        assert r.iloc[:252].isna().all()
        assert r.iloc[252] == pytest.approx(0.0)

    def test_negative_skip_rejected(self):
        with pytest.raises(ValueError, match="skip"):
            rolling_total_return(pd.Series([1.0, 2.0]), 1, skip=-1)


class TestRealizedVol:
    def test_constant_series_zero_vol(self):
        s = pd.Series(np.ones(100))
        rv = realized_vol(s.pct_change(), 20)
        tail = rv.dropna()
        assert (tail == 0).all()

    def test_annualization(self):
        rng = np.random.default_rng(7)
        rets = pd.Series(rng.normal(0, 0.01, 300))
        rv = realized_vol(rets, 60).dropna()
        assert (rv > 0.10).all() and (rv < 0.25).all()  # ~0.01*sqrt(252) ≈ 0.159


class TestIdioVolAndBeta:
    def test_beta_recovery(self):
        idx = pd.bdate_range("2020-01-01", periods=600)
        rng = np.random.default_rng(3)
        mkt = pd.Series(rng.normal(0, 0.01, 600), index=idx)
        frames = {}
        for beta in (0.5, 1.0, 1.5):
            frames[f"a{beta}"] = beta * mkt + pd.Series(rng.normal(0, 0.005, 600), index=idx)
        rets = pd.DataFrame(frames)
        betas = rolling_beta(rets, mkt, 252).dropna()
        assert betas.iloc[-1]["a0.5"] == pytest.approx(0.5, abs=0.15)
        assert betas.iloc[-1]["a1.0"] == pytest.approx(1.0, abs=0.15)
        assert betas.iloc[-1]["a1.5"] == pytest.approx(1.5, abs=0.15)
        iv = idio_vol(rets, mkt, 252).dropna()
        assert (iv.iloc[-1] < 0.10).all()  # residual vol ≈ 0.005*sqrt(252) ≈ 0.079

    def test_idio_vol_past_stable(self):
        idx = pd.bdate_range("2020-01-01", periods=400)
        rng = np.random.default_rng(11)
        mkt = pd.Series(rng.normal(0, 0.01, 400), index=idx)
        rets = pd.DataFrame({"x": mkt + rng.normal(0, 0.005, 400)}, index=idx)
        full = idio_vol(rets, mkt, 120)
        part = idio_vol(rets.iloc[:300], mkt.iloc[:300], 120)
        pd.testing.assert_frame_equal(full.iloc[:300], part)


class TestMaDistance:
    def test_uptrend_positive_distance(self):
        s = pd.Series(np.linspace(100, 150, 300))
        mad = ma_distance(s)
        assert (mad.dropna() > 0).all().all()  # price above rising MAs

    def test_windows(self):
        s = pd.Series(np.linspace(100, 150, 300))
        mad = ma_distance(s)
        assert list(mad.columns) == ["mad_63", "mad_126", "mad_189", "mad_252"]


class TestMisc:
    def test_max_drawdown(self):
        eq = pd.Series([100, 120, 90, 110, 60])
        assert max_drawdown(eq) == pytest.approx(-0.5)

    def test_cross_sectional_rank(self):
        scores = pd.DataFrame(
            {"a": [1.0, 2.0], "b": [3.0, np.nan], "c": [2.0, 1.0]},
            index=[pd.Timestamp("2020-01-01")] * 2,
        )
        r = cross_sectional_rank(scores)  # ascending=True: high score -> high percentile
        assert r.iloc[0]["b"] == pytest.approx(1.0)
        assert r.iloc[0]["a"] == pytest.approx(1 / 3)
        assert np.isnan(r.iloc[1]["b"])  # NaN stays unranked
        assert r.iloc[1]["c"] == pytest.approx(0.5)

        r2 = cross_sectional_rank(scores, ascending=False)  # low score -> high percentile
        assert r2.iloc[0]["b"] == pytest.approx(0.0)
        assert r2.iloc[0]["a"] == pytest.approx(2 / 3)
        assert np.isnan(r2.iloc[1]["b"])
