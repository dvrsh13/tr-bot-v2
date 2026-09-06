"""Performance metrics for equity curves."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trbot.indicators import TRADING_DAYS, max_drawdown


def compute_metrics(equity: pd.Series, turnover: pd.Series | None = None, commissions: float = 0.0) -> dict[str, float]:
    if len(equity) < 2:
        return {}
    rets = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    years = len(rets) / TRADING_DAYS
    cagr = (
        float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)
        if years > 0 and equity.iloc[-1] > 0
        else float("nan")
    )
    vol = float(rets.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(rets) > 1 else float("nan")
    sharpe = (
        float(rets.mean() / rets.std(ddof=1) * np.sqrt(TRADING_DAYS))
        if len(rets) > 1 and rets.std(ddof=1) > 0
        else float("nan")
    )
    downside = rets[rets < 0]
    sortino = (
        float(rets.mean() / downside.std(ddof=1) * np.sqrt(TRADING_DAYS))
        if len(downside) > 1 and downside.std(ddof=1) > 0
        else float("nan")
    )
    mdd = max_drawdown(equity)
    calmar = float(cagr / abs(mdd)) if mdd < 0 and np.isfinite(cagr) else float("nan")
    out = {
        "total_return": total_return,
        "cagr": cagr,
        "ann_vol": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "win_rate_daily": float((rets > 0).mean()) if len(rets) else float("nan"),
        "n_days": int(len(rets)),
    }
    if turnover is not None:
        out["turnover_ann"] = float(turnover.dropna().sum() / max(years, 1e-9))
    if commissions:
        out["commissions_total"] = float(commissions)
    return out


def benchmark_buyhold(close: pd.Series, initial_capital: float) -> pd.Series:
    """Equal-cash buy&hold of a single price series (no rebalancing)."""
    shares = initial_capital / float(close.iloc[0])
    return close * shares
