"""Strategy base + registry.

Contract: a strategy receives a snapshot of history and returns TARGET WEIGHTS
per symbol on each date it is evaluated (the engine calls it only on rebalance
dates and only with data ≤ that date). Strategies PROPOSE; they never execute.
The risk engine must approve every weight before the broker sees it.

All strategies are long-only, weights in [0, 1], gross exposure ≤ 1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from trbot.indicators import (
    cross_sectional_rank,
    idio_vol,
    realized_vol,
    rolling_total_return,
)


@dataclass(frozen=True)
class StrategyInput:
    """Wide frames of per-symbol history, ending at the evaluation date."""

    close: pd.DataFrame  # dates × symbols
    returns: pd.DataFrame  # dates × symbols (pct_change of close)
    market_close: pd.Series  # equal-weight universe close (proxy market)


class Strategy(ABC):
    name: str = "base"

    def __init__(self, **params) -> None:
        self.params = dict(params)
        self.validate_params()

    @abstractmethod
    def validate_params(self) -> None: ...

    @abstractmethod
    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        """Return a 1-row (date × symbol) weight frame for the snapshot's last date."""


def _select_top_n(scores: pd.Series, top_n: int) -> pd.Series:
    """Equal weights 1/top_n over the top_n scores; NaN scores excluded."""
    ranked = scores.dropna().sort_values(ascending=False)
    picked = ranked.index[:top_n]
    if len(picked) == 0:
        return pd.Series(dtype="float64")
    return pd.Series(1.0 / len(picked), index=picked)


class XSMomentum(Strategy):
    """Cross-sectional 12-1 momentum (Jegadeesh & Titman 1993): hold the top_n
    names by total return over [t-lookback, t-skip], skipping the most recent
    `skip` days to avoid short-term reversal (Jegadeesh 1990)."""

    name = "xs_momentum"

    def validate_params(self) -> None:
        p = self.params
        self.lookback = int(p.get("lookback", 252))
        self.skip = int(p.get("skip", 21))
        self.top_n = int(p.get("top_n", 10))
        if not (60 <= self.lookback <= 504):
            raise ValueError("lookback must be in [60, 504]")
        if not (0 <= self.skip < self.lookback):
            raise ValueError("skip must be in [0, lookback)")
        if self.top_n < 1:
            raise ValueError("top_n must be >= 1")

    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        t = snap.close.index[-1]
        score = rolling_total_return(snap.close, self.lookback, self.skip).iloc[-1]
        return _select_top_n(score, self.top_n).to_frame(t).T


class TSMomentumVol(Strategy):
    """Time-series momentum with per-name vol scaling (Moskowitz-Ooi-Pedersen 2012
    + Moreira-Muir 2017 overlay): long names whose trailing return is positive,
    sized by inverse realized vol toward a target vol, gross-capped.

    Among positive-sign names, only the `max_names` with the strongest trend are
    held — the risk engine's max_positions cap must be satisfiable by
    construction (v2 lesson: proposals exceeding it get rejected and the
    strategy silently never trades).
    """

    name = "tsmom_vol"

    def validate_params(self) -> None:
        p = self.params
        self.lookback = int(p.get("lookback", 252))
        self.vol_window = int(p.get("vol_window", 60))
        self.target_vol = float(p.get("target_vol", 0.12))
        self.scalar_lo = float(p.get("scalar_lo", 0.5))
        self.scalar_hi = float(p.get("scalar_hi", 1.5))
        self.max_names = int(p.get("max_names", 10))
        if self.lookback < 60:
            raise ValueError("lookback must be >= 60")
        if self.vol_window < 10:
            raise ValueError("vol_window must be >= 10")
        if not (0.01 <= self.target_vol <= 2.0):
            raise ValueError("target_vol must be in [0.01, 2.0]")
        if self.max_names < 1:
            raise ValueError("max_names must be >= 1")

    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        t = snap.close.index[-1]
        trend = rolling_total_return(snap.close, self.lookback, 0).iloc[-1]
        vol = realized_vol(snap.returns, self.vol_window).iloc[-1]
        long_names = trend.index[trend.fillna(-np.inf) > 0]
        if len(long_names) == 0:
            return pd.DataFrame([{s: 0.0 for s in snap.close.columns}], index=[t])
        # strongest trends first, bounded by max_names
        long_names = trend.loc[long_names].sort_values(ascending=False).index[: self.max_names]
        scalar = (self.target_vol / vol.loc[long_names]).clip(self.scalar_lo, self.scalar_hi)
        raw = scalar / scalar.sum()  # normalized vol-scaled long book, gross = 1
        row = pd.Series(0.0, index=snap.close.columns)
        row[raw.index] = raw
        return row.to_frame(t).T


class TrendFactor(Strategy):
    """Trend factor (Han-Yang-Zhou 2013): rank names by the average cross-sectional
    percentile of MA-distance characteristics (price / MA_k - 1 for k in days)."""

    name = "trend_factor"

    def validate_params(self) -> None:
        p = self.params
        self.windows = tuple(int(w) for w in p.get("windows", (63, 126, 189, 252)))
        self.top_n = int(p.get("top_n", 10))
        if not self.windows or any(w < 20 for w in self.windows):
            raise ValueError("windows must contain values >= 20")
        if self.top_n < 1:
            raise ValueError("top_n must be >= 1")

    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        t = snap.close.index[-1]
        per_window = []
        for w in self.windows:
            mad = snap.close.iloc[-1] / snap.close.rolling(w, min_periods=w).mean().iloc[-1] - 1
            per_window.append(cross_sectional_rank(mad.to_frame("s").T).iloc[0])
        composite = pd.concat(per_window, axis=1).mean(axis=1)
        return _select_top_n(composite, self.top_n).to_frame(t).T


class LowVol(Strategy):
    """Defensive low-volatility tilt (Ang et al. 2006): hold the names with the
    lowest idiosyncratic volatility vs the equal-weight universe, inverse-vol
    weighted (ERC-lite, Maillard et al. 2010)."""

    name = "lowvol"

    def validate_params(self) -> None:
        p = self.params
        self.vol_window = int(p.get("vol_window", 252))
        self.top_n = int(p.get("top_n", 10))
        if self.vol_window < 60:
            raise ValueError("vol_window must be >= 60")
        if self.top_n < 1:
            raise ValueError("top_n must be >= 1")

    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        t = snap.close.index[-1]
        mkt_ret = snap.market_close.pct_change()
        iv = idio_vol(snap.returns, mkt_ret, self.vol_window).iloc[-1]
        ranked = iv.dropna().sort_values(ascending=True)  # lowest idio vol first
        picked = ranked.index[: self.top_n]
        if len(picked) == 0:
            return pd.DataFrame([{s: 0.0 for s in snap.close.columns}], index=[t])
        inv = 1.0 / ranked.loc[picked].clip(lower=1e-4)
        weights = inv / inv.sum()
        row = pd.Series(0.0, index=snap.close.columns)
        row[weights.index] = weights
        return row.to_frame(t).T


class MomentumDefenseBlend(Strategy):
    """Composite blend (Asness-Moskowitz-Pedersen 2013 insight): an offense sleeve
    (momentum+trend composite) and a defense sleeve (low-vol), capital split by
    `defense_weight`. Negative correlation between sleeves is the point."""

    name = "mom_def_blend"

    def validate_params(self) -> None:
        p = self.params
        self.top_n = int(p.get("top_n", 8))
        self.defense_weight = float(p.get("defense_weight", 0.3))
        if not (0.0 <= self.defense_weight <= 0.6):
            raise ValueError("defense_weight must be in [0, 0.6]")
        if self.top_n < 1:
            raise ValueError("top_n must be >= 1")

    def target_weights(self, snap: StrategyInput) -> pd.DataFrame:
        t = snap.close.index[-1]
        offense_n = max(1, self.top_n)
        mom = cross_sectional_rank(rolling_total_return(snap.close, 252, 21).iloc[-1].to_frame("s").T).iloc[0]
        trd = cross_sectional_rank(
            (snap.close.iloc[-1] / snap.close.rolling(126, min_periods=126).mean().iloc[-1] - 1).to_frame("s").T
        ).iloc[0]
        offense_score = (mom + trd) / 2
        offense = _select_top_n(offense_score, offense_n) * (1 - self.defense_weight)

        mkt_ret = snap.market_close.pct_change()
        iv = idio_vol(snap.returns, mkt_ret, 252).iloc[-1]
        low = iv.dropna().sort_values(ascending=True).index[:offense_n]
        if len(low) > 0:
            inv = 1.0 / iv.loc[low].clip(lower=1e-4)
            defense = (inv / inv.sum()) * self.defense_weight
        else:
            defense = pd.Series(dtype="float64")

        combined = pd.concat([offense, defense])
        combined = combined.groupby(level=0).sum()  # overlap-safe
        row = pd.Series(0.0, index=snap.close.columns)
        row[combined.index] = combined
        return row.to_frame(t).T


REGISTRY: dict[str, type[Strategy]] = {
    cls.name: cls  # type: ignore[attr-defined]
    for cls in (XSMomentum, TSMomentumVol, TrendFactor, LowVol, MomentumDefenseBlend)
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in REGISTRY:
        raise ValueError(f"unknown strategy: {name!r} (known: {sorted(REGISTRY)})")
    return REGISTRY[name](**(params or {}))
