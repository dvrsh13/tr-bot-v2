"""Strict configuration layer with paper-only mode guard.

Safety contract: only SIMULATION and PAPER modes exist. Anything resembling live
trading fails at config load. Order submission is double-gated: config
``orders.enabled`` AND environment ``TRBOT_ORDERS_ENABLED=true`` — neither is
sufficient alone.
"""

from __future__ import annotations

import copy
import os
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

FORBIDDEN_MODES = {"live", "real", "production", "prod", "broker", "money", ""}
PAPER_BASE_URL = "https://paper-api.alpaca.markets"
DATA_BASE_URL = "https://data.alpaca.markets"


class Mode(StrEnum):
    SIMULATION = "SIMULATION"
    PAPER = "PAPER"


class DataConfig(BaseModel):
    provider: str = "parquet"  # parquet | synthetic | csv
    cache_dir: str = "data/cache"
    universe_path: str = "config/universe_us_core.csv"
    start: str = "2019-01-01"
    end: str | None = None  # None = latest available
    synthetic_days: int = Field(default=1500, ge=300)
    synthetic_symbols: int = Field(default=12, ge=2)

    @field_validator("provider")
    @classmethod
    def _known_provider(cls, v: str) -> str:
        if v not in {"parquet", "synthetic", "csv"}:
            raise ValueError(f"unknown data provider: {v!r}")
        return v


class BacktestConfig(BaseModel):
    initial_capital: float = Field(default=100_000.0, gt=0)
    commission_bps: float = Field(default=1.0, ge=0)  # per side, of notional
    slippage_bps: float = Field(default=2.0, ge=0)
    rebalance_every: int = Field(default=21, ge=1)  # trading days
    max_positions: int = Field(default=10, ge=1)
    max_position_weight: float = Field(default=0.15, gt=0, le=1)
    max_gross_exposure: float = Field(default=1.0, gt=0, le=1)
    target_vol_ann: float = Field(default=0.12, gt=0, le=2)
    vol_lookback_days: int = Field(default=60, ge=10)
    min_history_days: int = Field(default=280, ge=60)


class RiskConfig(BaseModel):
    max_drawdown_kill: float = Field(default=0.10, gt=0, le=1)
    order_notional_cap: float = Field(default=0.10, gt=0, le=1)
    cooldown_days_after_kill: int = Field(default=5, ge=0)
    # halt = permanent until manual reset (live semantics); cooldown = auto-resume
    # after cooldown_days trading days (research semantics — measures the
    # strategy across the full sample instead of one crash)
    policy: str = "halt"
    # reject = fail closed on cap violations (live default); scale = cap-and-
    # renormalize with an audit stamp (research convenience ONLY — the runner
    # always uses reject)
    on_violation: str = "reject"

    @field_validator("policy")
    @classmethod
    def _known_policy(cls, v: str) -> str:
        if v not in {"halt", "cooldown"}:
            raise ValueError(f"unknown kill policy: {v!r} (halt|cooldown)")
        return v

    @field_validator("on_violation")
    @classmethod
    def _known_violation(cls, v: str) -> str:
        if v not in {"reject", "scale"}:
            raise ValueError(f"unknown on_violation: {v!r} (reject|scale)")
        return v


class OrdersConfig(BaseModel):
    enabled: bool = False  # must pair with TRBOT_ORDERS_ENABLED=true (double gate)


class BrokerConfig(BaseModel):
    base_url: str = PAPER_BASE_URL
    data_url: str = DATA_BASE_URL
    key_id_env: str = "ALPACA_KEY_ID"
    secret_env: str = "ALPACA_SECRET_KEY"
    feed: str = "iex"

    @field_validator("base_url", "data_url")
    @classmethod
    def _paper_only_urls(cls, v: str) -> str:
        low = v.lower()
        if "live" in low or "prod" in low or "real" in low:
            raise ValueError(f"refusing non-paper broker url: {v!r}")
        allowed = {PAPER_BASE_URL, DATA_BASE_URL}
        if v not in allowed:
            raise ValueError(f"broker url not in paper allowlist: {v!r}")
        return v


class StrategyConfig(BaseModel):
    name: str = "xs_momentum"
    params: dict[str, float | int | str] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    level: str = "INFO"
    dir: str = "logs"


class Settings(BaseModel):
    mode: Mode = Mode.SIMULATION
    data: DataConfig = Field(default_factory=DataConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    orders: OrdersConfig = Field(default_factory=OrdersConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("mode", mode="before")
    @classmethod
    def _mode_guard(cls, v: object) -> object:
        if v is None:
            raise ValueError("mode must not be empty (paper-only guard)")
        s = str(v).strip().lower()
        if s in FORBIDDEN_MODES:
            raise ValueError(f"refusing forbidden/empty mode: {v!r} (only SIMULATION/PAPER exist)")
        if s == "simulation":
            return Mode.SIMULATION
        if s == "paper":
            return Mode.PAPER
        raise ValueError(f"unknown mode: {v!r} (only SIMULATION/PAPER exist)")

    @model_validator(mode="after")
    def _orders_double_gate(self) -> Settings:
        if self.orders.enabled and self.mode is not Mode.PAPER:
            raise ValueError("orders.enabled requires mode=PAPER")
        return self

    @property
    def orders_actually_enabled(self) -> bool:
        """True only when both gates are open: config flag AND env var."""
        return self.orders.enabled and os.environ.get("TRBOT_ORDERS_ENABLED", "").lower() == "true"


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_settings(path: str | Path | None = None, overrides: dict | None = None) -> Settings:
    """Load YAML settings, deep-merge optional overrides dict, validate."""
    raw: dict = {}
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"settings file not found: {p}")
        loaded = yaml.safe_load(p.read_text())
        if loaded is not None:
            if not isinstance(loaded, dict):
                raise ValueError(f"settings file must contain a mapping: {p}")
            raw = loaded
    if overrides:
        raw = _deep_merge(raw, overrides)
    return Settings.model_validate(raw)
