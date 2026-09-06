"""Probability of Backtest Overfitting (PBO) via CSCV-style combinatorial splits.

Bailey, Borwein, López de Prado & Zhu (2017): split the timeline into S blocks;
for every combination of S/2 blocks treated as "in-sample", pick the best
configuration by IS Sharpe and check its relative rank out-of-sample (the
complement blocks). PBO = fraction of splits where the IS-best configuration
performs below the OOS median — i.e., the selection procedure picked noise.

Engine runs happen ONCE per configuration; the CSCV machinery is numpy over the
resulting T×N daily-returns matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from trbot.backtest.engine import run_backtest
from trbot.config import Settings
from trbot.indicators import TRADING_DAYS


@dataclass
class PBOResult:
    pbo: float
    n_configs: int
    n_splits: int
    is_best_oos_ranks: list[float]  # relative rank of IS-best config per split
    config_labels: list[str]
    per_config_oos_sharpe: dict[str, float]

    def summary(self) -> str:
        verdict = "HIGH overfitting risk" if self.pbo > 0.5 else ("moderate" if self.pbo > 0.2 else "low")
        return f"PBO {self.pbo:.2f} over {self.n_splits} splits, {self.n_configs} configs — {verdict}"


def _sharpe(returns: np.ndarray) -> float:
    r = returns[~np.isnan(returns)]
    if len(r) < 3 or r.std(ddof=1) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def cscv_pbo(returns_matrix: pd.DataFrame, n_blocks: int = 8) -> PBOResult:
    """returns_matrix: dates × configs of DAILY strategy returns on identical dates."""
    R = returns_matrix.dropna(how="all").to_numpy()
    n_dates, n_configs = R.shape
    if n_dates < n_blocks * 20:
        raise ValueError(f"need >= {n_blocks * 20} dates, got {n_dates}")
    if n_configs < 2:
        raise ValueError("need >= 2 configurations")

    edges = [int(n_dates * k / n_blocks) for k in range(n_blocks + 1)]
    blocks = [(edges[k], edges[k + 1]) for k in range(n_blocks)]
    half = n_blocks // 2
    is_best_ranks: list[float] = []

    for combo in combinations(range(n_blocks), half):
        is_idx = np.concatenate([np.arange(*blocks[b]) for b in combo])
        oos_idx = np.concatenate([np.arange(*blocks[b]) for b in range(n_blocks) if b not in combo])
        is_sharpes = np.array([_sharpe(R[is_idx, c]) for c in range(n_configs)])
        if np.all(np.isnan(is_sharpes)):
            continue
        best = int(np.nanargmax(is_sharpes))
        oos_sharpes = np.array([_sharpe(R[oos_idx, c]) for c in range(n_configs)])
        order = pd.Series(oos_sharpes).rank(ascending=True, pct=True).to_numpy()
        is_best_ranks.append(float(order[best]))

    pbo = float(np.mean([r < 0.5 for r in is_best_ranks])) if is_best_ranks else float("nan")
    oos_full = {c: _sharpe(R[:, c]) for c in range(n_configs)}
    labels = [str(c) for c in returns_matrix.columns]
    return PBOResult(
        pbo=pbo,
        n_configs=n_configs,
        n_splits=len(is_best_ranks),
        is_best_oos_ranks=is_best_ranks,
        config_labels=labels,
        per_config_oos_sharpe={labels[c]: oos_full[c] for c in range(n_configs)},
    )


def pbo_from_configs(
    frames: dict[str, pd.DataFrame], strategy_name: str, param_grid: list[dict], settings: Settings, n_blocks: int = 8
) -> PBOResult:
    """Run each configuration once and compute PBO over the returned equity curves."""
    if not param_grid:
        raise ValueError("param_grid is empty")
    curves = {}
    for i, params in enumerate(param_grid):
        res = run_backtest(frames, _build(strategy_name, params), settings)
        label = f"cfg{i}:{_short(params)}"
        curves[label] = res.equity.pct_change()
    matrix = pd.DataFrame(curves).dropna(how="all")
    return cscv_pbo(matrix, n_blocks=n_blocks)


def _build(name: str, params: dict):
    from trbot.strategies.base import build_strategy

    return build_strategy(name, params)


def _short(params: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(params.items()))[:40]
