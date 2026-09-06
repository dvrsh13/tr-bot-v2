"""Vectorized indicators over daily OHLCV frames.

No-lookahead convention: every function here only uses data at or before the
current row (pure rolling/backward-looking transforms). The backtest engine
additionally slices frames to ``data[:i+1]`` before calling signals, so the
guarantee holds by construction; these functions must never introduce forward
bias themselves (no centering, no negative shifts on the lookback side).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def realized_vol(returns: pd.Series, window: int, trading_days: int = TRADING_DAYS) -> pd.Series:
    """Annualized rolling realized volatility of returns."""
    return returns.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(trading_days)


def rolling_total_return(close: pd.Series, lookback: int, skip: int = 0) -> pd.Series:
    """Total return from t-lookback to t-1-skip (skip excludes the most recent bars).

    ``skip=21`` implements the classic 12-1 momentum convention (skip last month)
    justified by short-horizon reversal (Jegadeesh 1990).
    """
    if skip < 0:
        raise ValueError("skip must be >= 0")
    if skip:
        shifted = close.shift(skip)
        return shifted / shifted.shift(lookback - skip) - 1
    return close / close.shift(lookback) - 1


def idio_vol(
    returns: pd.DataFrame, market_returns: pd.Series, window: int, trading_days: int = TRADING_DAYS
) -> pd.DataFrame:
    """Rolling idiosyncratic volatility of each column vs market (Ang et al. 2006).

    For each asset: residual = r_i - beta_i * r_m, beta estimated on the same
    rolling window; idio vol = std(residual) annualized. Pure backward-looking.
    """
    out = {}
    for col in returns.columns:
        r = returns[col]
        cov = r.rolling(window, min_periods=window).cov(market_returns)
        var = market_returns.rolling(window, min_periods=window).var(ddof=1)
        beta = cov / var.replace(0, np.nan)
        resid = r - beta * market_returns
        out[col] = resid.rolling(window, min_periods=window).std(ddof=1) * np.sqrt(trading_days)
    return pd.DataFrame(out, index=returns.index)


def rolling_beta(returns: pd.DataFrame, market_returns: pd.Series, window: int) -> pd.DataFrame:
    """Rolling market beta per asset (Frazzini-Pedersen BAB input)."""
    cov = returns.rolling(window, min_periods=window).cov(market_returns)
    var = market_returns.rolling(window, min_periods=window).var(ddof=1)
    return cov.div(var.replace(0, np.nan), axis=0)


def ma_distance(close: pd.Series, windows: tuple[int, ...] = (63, 126, 189, 252)) -> pd.DataFrame:
    """Moving-average distance characteristics: price / MA_k - 1 (trend factor, Han-Yang-Zhou 2013).

    Positive = price above its k-day MA (uptrend). Higher distance predicts
    higher future returns in the paper's cross-sectional sort.
    """
    out = {}
    for w in windows:
        out[f"mad_{w}"] = close / sma(close, w) - 1
    return pd.DataFrame(out, index=close.index)


def max_drawdown(equity: pd.Series) -> float:
    """Max drawdown as a negative float (worst peak-to-trough)."""
    if len(equity) == 0:
        return 0.0
    running_max = equity.cummax()
    dd = equity / running_max - 1
    return float(dd.min())


def cross_sectional_rank(scores: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    """Per-date cross-sectional percentile in [0, 1].

    With ``ascending=True`` (default), the highest raw score gets percentile 1.0
    (e.g. momentum). With ``ascending=False``, the lowest raw score gets 1.0
    (e.g. low-vol). NaN scores stay NaN (unrankable — e.g. insufficient history);
    percentiles occupy [0,1] among *rankable* names only.
    """
    pct = scores.rank(axis=1, ascending=True, pct=True, na_option="keep")
    if ascending:
        return pct
    return 1 - pct
