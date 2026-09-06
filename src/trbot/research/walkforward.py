"""Walk-forward validation: k anchored folds, each fold's OOS window evaluated
on equity from an engine run that saw history up to that point (warmup + prior
folds), matching the live experience of a strategy that has been running.

Fails loudly when a fold is shorter than the strategy warmup (v1 lesson: silent
untradeable folds).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from trbot.backtest.engine import run_backtest
from trbot.config import Settings
from trbot.indicators import TRADING_DAYS
from trbot.strategies.base import Strategy


@dataclass
class FoldResult:
    fold: int
    start: pd.Timestamp
    end: pd.Timestamp
    oos_return: float
    oos_sharpe: float
    max_drawdown: float


@dataclass
class WalkForwardResult:
    folds: list[FoldResult]
    aggregate: dict[str, float]

    def summary(self) -> str:
        a = self.aggregate
        return (
            f"OOS return {a['oos_return_total']:+.2%}, OOS Sharpe {a['oos_sharpe']:.2f}, "
            f"worst fold DD {a['worst_fold_dd']:.2%} over {len(self.folds)} folds"
        )


def walk_forward(
    frames: dict[str, pd.DataFrame], strategy: Strategy, settings: Settings, n_folds: int = 4, min_oos_days: int = 120
) -> WalkForwardResult:
    from trbot.data.schema import to_wide

    wide = to_wide(frames, "close")
    total = len(wide)
    warmup = settings.backtest.min_history_days
    oos_total = total - warmup
    if oos_total < n_folds * min_oos_days:
        raise ValueError(
            f"OOS span {oos_total} bars too short for {n_folds} folds of {min_oos_days}+ days "
            f"(warmup {warmup}, total {total})"
        )

    fold_edges = [warmup + int(oos_total * k / n_folds) for k in range(n_folds + 1)]
    folds: list[FoldResult] = []
    oos_returns_all: list[float] = []

    for k in range(n_folds):
        start_i, end_i = fold_edges[k], fold_edges[k + 1]
        if end_i - start_i < min_oos_days:
            raise ValueError(f"fold {k} too short: {end_i - start_i} < {min_oos_days}")
        # run engine on everything up to fold end (it only trades after warmup)
        sub = {s: df.iloc[:end_i] for s, df in frames.items()}
        res = run_backtest(sub, strategy, settings)
        eq = res.equity
        start_t, end_t = wide.index[start_i], wide.index[end_i - 1]
        eq_win = eq.loc[start_t:end_t]
        if len(eq_win) < 10:
            raise ValueError(f"fold {k} produced {len(eq_win)} equity bars")
        rets = eq_win.pct_change().dropna()
        oos_ret = float(eq_win.iloc[-1] / eq_win.iloc[0] - 1)
        oos_sharpe = (
            float(rets.mean() / rets.std(ddof=1) * np.sqrt(TRADING_DAYS))
            if len(rets) > 2 and rets.std(ddof=1) > 0
            else float("nan")
        )
        oos_returns_all.extend(rets.tolist())
        from trbot.indicators import max_drawdown

        folds.append(
            FoldResult(
                fold=k,
                start=start_t,
                end=end_t,
                oos_return=oos_ret,
                oos_sharpe=oos_sharpe,
                max_drawdown=max_drawdown(eq_win),
            )
        )

    rets_all = pd.Series(oos_returns_all)
    agg = {
        "oos_return_total": float(np.prod([1 + f.oos_return for f in folds]) - 1),
        "oos_sharpe": float(rets_all.mean() / rets_all.std(ddof=1) * np.sqrt(TRADING_DAYS))
        if rets_all.std(ddof=1) > 0
        else float("nan"),
        "worst_fold_dd": float(min(f.max_drawdown for f in folds)),
        "mean_fold_return": float(np.mean([f.oos_return for f in folds])),
    }
    return WalkForwardResult(folds=folds, aggregate=agg)
