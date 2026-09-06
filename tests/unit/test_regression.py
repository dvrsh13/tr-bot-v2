"""Golden-file regression: pins the exact synthetic selftest equity curve.

Any intentional engine change that moves these values must be regenerated and
documented in BUILD_LOG.md (v1 convention). Runs in seconds, fully deterministic
(crc32-seeded synthetic data).
"""

from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from trbot.backtest.engine import run_strategy_backtest
from trbot.config import Settings
from trbot.data.providers import SyntheticProvider

GOLDEN_FINAL_EQUITY = 127826.3155
GOLDEN_EQUITY_SHA16 = "2743307f14896f96"
GOLDEN_SHARPE = 0.789638


@pytest.fixture(scope="module")
def golden_result():
    settings = Settings.model_validate(
        {
            "backtest": {"min_history_days": 280, "rebalance_every": 21},
            "strategy": {"name": "xs_momentum", "params": {"top_n": 10}},
        }
    )
    frames = SyntheticProvider(days=900, end=pd.Timestamp("2025-06-30")).load([f"S{i}" for i in range(10)])
    return run_strategy_backtest(frames, "xs_momentum", {"top_n": 10}, settings)


def test_golden_final_equity(golden_result):
    assert golden_result.equity.iloc[-1] == pytest.approx(GOLDEN_FINAL_EQUITY, abs=0.01)


def test_golden_curve_digest(golden_result):
    digest = hashlib.sha256(golden_result.equity.to_numpy().tobytes()).hexdigest()[:16]
    assert digest == GOLDEN_EQUITY_SHA16


def test_golden_sharpe(golden_result):
    assert golden_result.metrics["sharpe"] == pytest.approx(GOLDEN_SHARPE, abs=1e-5)
