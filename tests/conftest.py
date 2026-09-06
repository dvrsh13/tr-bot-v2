"""Shared fixtures: deterministic frames + settings."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trbot.config import Settings  # noqa: E402
from trbot.data.providers import SyntheticProvider  # noqa: E402


@pytest.fixture(scope="session")
def synth_frames():
    prov = SyntheticProvider(days=800, end=pd.Timestamp("2025-06-30"))
    return prov.load([f"S{i:02d}" for i in range(12)])


@pytest.fixture
def sim_settings():
    return Settings.model_validate(
        {
            "mode": "simulation",
            "backtest": {
                "initial_capital": 100_000.0,
                "commission_bps": 1.0,
                "slippage_bps": 2.0,
                "rebalance_every": 21,
                "max_positions": 8,
                "max_position_weight": 0.2,
                "min_history_days": 280,
            },
            "strategy": {"name": "xs_momentum", "params": {"lookback": 252, "skip": 21, "top_n": 5}},
        }
    )
