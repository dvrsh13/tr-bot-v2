"""Market data providers: synthetic (seeded), CSV, Parquet, and Alpaca REST bars.

Provider protocol: ``load(symbols) -> dict[symbol, standardized OHLCV frame]``.
The Alpaca provider is the primary *first-party* data path (paper credentials);
CSV/Parquet are cached/snapshot paths; synthetic exists for deterministic tests.
No web scraping providers by design (v1 lesson: scraped sources break silently).
"""

from __future__ import annotations

import json
import os
import urllib.request
import zlib
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from trbot.config import BrokerConfig
from trbot.data.schema import standardize_ohlcv  # re-exported


class Provider(Protocol):
    def load(self, symbols: list[str]) -> dict[str, pd.DataFrame]: ...


# ---------------------------------------------------------------- synthetic


def _seed_for(symbol: str) -> int:
    """Stable, process-independent seed (v1 lesson: hash() is process-salted)."""
    return zlib.crc32(symbol.encode("utf-8"))


class SyntheticProvider:
    """Seeded regime-switching GBM per symbol + a shared market factor.

    Deterministic across processes for a fixed symbol list; sufficient for
    testing strategy plumbing (not for performance claims).
    """

    def __init__(self, days: int = 1500, end: pd.Timestamp | None = None, market_cap: float = 0.0) -> None:
        self.days = days
        self.end = end or pd.Timestamp.today().normalize()

    def load(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        idx = pd.bdate_range(end=self.end, periods=self.days)
        rng = np.random.default_rng(_seed_for("MARKET-FACTOR"))
        mkt_ret = np.zeros(self.days)
        regime = 0.0  # persistent drift state
        for i in range(self.days):
            if rng.random() < 0.01:
                regime = rng.normal(0, 1) * 0.001
            mkt_ret[i] = 0.0002 + regime + rng.normal(0, 0.010)
        frames = {}
        for sym in symbols:
            srng = np.random.default_rng(_seed_for(sym))
            beta = float(srng.uniform(0.6, 1.4))
            idio = srng.normal(0, 0.012, size=self.days)
            drift = float(srng.uniform(-0.0002, 0.0006))
            rets = drift + beta * mkt_ret + idio
            close = 50.0 * np.exp(np.cumsum(rets))
            open_ = close * (1 + srng.normal(0, 0.002, size=self.days))
            spread = np.abs(srng.normal(0.012, 0.004, size=self.days))
            high = np.maximum(open_, close) * (1 + spread)
            low = np.minimum(open_, close) * (1 - spread)
            vol = np.exp(srng.normal(14, 0.5, size=self.days))
            df = pd.DataFrame(
                {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
                index=idx,
            )
            frames[sym] = df
        return frames


# ---------------------------------------------------------------- file paths


class ParquetProvider:
    """Loads ``<cache_dir>/<SYMBOL>.parquet`` snapshots."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.exists():
            raise FileNotFoundError(f"parquet cache dir not found: {self.cache_dir}")

    def load(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        frames = {}
        for sym in symbols:
            p = self.cache_dir / f"{sym}.parquet"
            if not p.exists():
                continue
            frames[sym] = standardize_ohlcv(pd.read_parquet(p).reset_index())
        return frames


class CSVProvider:
    """Loads ``<cache_dir>/<SYMBOL>.csv`` snapshots."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.exists():
            raise FileNotFoundError(f"csv cache dir not found: {self.cache_dir}")

    def load(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        frames = {}
        for sym in symbols:
            p = self.cache_dir / f"{sym}.csv"
            if not p.exists():
                continue
            frames[sym] = standardize_ohlcv(pd.read_csv(p))
        return frames


# ---------------------------------------------------------------- alpaca rest


class AlpacaBarsProvider:
    """First-party daily bars via Alpaca Market Data REST (free IEX feed).

    Notes baked in from v1's live-fire lessons:
    - the multi-symbol bars endpoint returns a dict keyed by symbol (not a list);
    - batch requests respect the free tier: <= 25 symbols/request, throttle left
      to the caller;
    - credentials come from the environment only, never from disk files.
    """

    PAGE_LIMIT = 10_000

    def __init__(self, broker: BrokerConfig, start: str, end: str | None = None) -> None:
        self.broker = broker
        self.start = start
        self.end = end
        self._last_response_bytes = 0

    def _credentials(self) -> tuple[str, str]:
        key_id = os.environ.get(self.broker.key_id_env, "")
        secret = os.environ.get(self.broker.secret_env, "")
        if not key_id or not secret:
            raise RuntimeError(f"missing credentials: set {self.broker.key_id_env} and {self.broker.secret_env}")
        return key_id, secret

    def fetch_batch(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        if len(symbols) > 25:
            raise ValueError("free tier allows <= 25 symbols per bars request")
        key_id, secret = self._credentials()
        params = [
            "timeframe=1Day",
            f"start={self.start}",
            f"feed={self.broker.feed}",
            "adjustment=split",
            f"limit={self.PAGE_LIMIT}",
        ]
        if self.end:
            params.append(f"end={self.end}")
        url = f"{self.broker.data_url}/v2/stocks/bars?symbols={','.join(symbols)}&" + "&".join(params)
        req = urllib.request.Request(
            url,
            headers={
                "APCA-API-KEY-ID": key_id,
                "APCA-API-SECRET-KEY": secret,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - allowlisted https host
            payload = json.loads(resp.read().decode("utf-8"))
        return self.parse_bars_response(payload)

    @staticmethod
    def parse_bars_response(payload: dict) -> dict[str, pd.DataFrame]:
        """Parse /v2/stocks/bars payload: bars keyed by symbol (v1 bug fixed by design)."""
        bars = payload.get("bars")
        if bars is None:
            raise ValueError("unexpected bars payload: missing 'bars'")
        if not isinstance(bars, dict):
            raise ValueError("unexpected bars payload shape: expected dict keyed by symbol")
        frames: dict[str, pd.DataFrame] = {}
        for sym, rows in bars.items():
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df = df.rename(
                columns={
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                    "t": "date",
                    "n": "trades",
                    "vw": "vwap",
                }
            )
            frames[sym] = standardize_ohlcv(df)
        return frames


def build_provider(data_cfg, broker_cfg: BrokerConfig | None = None) -> Provider:
    kind = data_cfg.provider
    if kind == "synthetic":
        return SyntheticProvider(days=data_cfg.synthetic_days)
    if kind == "parquet":
        return ParquetProvider(data_cfg.cache_dir)
    if kind == "csv":
        return CSVProvider(data_cfg.cache_dir)
    raise ValueError(f"unknown provider: {kind}")
