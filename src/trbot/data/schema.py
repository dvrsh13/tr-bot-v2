"""Data standardization + validation for daily OHLCV bars."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a per-symbol bar frame to canonical form: unnamed UTC-day DatetimeIndex,
    lowercase columns (open/high/low/close/volume first, extras preserved), sorted, float64.
    Column-name matching is case-insensitive (Yahoo returns Capitalized names)."""
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        time_col = next((c for c in out.columns if str(c).lower() in ("date", "timestamp", "t", "time", "index")), None)
        if time_col is not None:
            out = out.set_index(time_col)
    out.index = pd.to_datetime(out.index, utc=True)
    out.index = out.index.tz_convert("UTC").tz_localize(None).normalize()
    out.index.name = None  # canonical: unnamed DatetimeIndex
    out = out.rename(columns={c: str(c).lower() for c in out.columns})
    missing = [c for c in REQUIRED_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {missing}")
    ordered = list(REQUIRED_COLUMNS) + [c for c in out.columns if c not in REQUIRED_COLUMNS]
    out = (
        out[ordered]
        .astype({"open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"})
        .sort_index()
    )
    if out.index.has_duplicates:
        out = out.groupby(level=0).last()
    return out


def repair_envelope(df: pd.DataFrame) -> pd.DataFrame:
    """Clamp high/low to contain open/close exactly.

    Handles upstream adjustment artifacts (e.g. Yahoo auto_adjust rows where
    low/close differ by float epsilon). Deterministic, idempotent, and logged
    by callers — never silently rewrites genuine bad data (validation still
    runs after repair).
    """
    out = df.copy()
    out["high"] = out[["high", "open", "close"]].max(axis=1)
    out["low"] = out[["low", "open", "close"]].min(axis=1)
    return out


def validate_ohlcv(
    symbol: str, df: pd.DataFrame, *, min_history: int = 60, max_future_date: pd.Timestamp | None = None
) -> list[str]:
    """Ten deterministic quality checks. Returns list of problems (empty = pass)."""
    problems: list[str] = []
    if df.empty:
        return [f"{symbol}: empty frame"]
    if df.index.duplicated().any():
        problems.append(f"{symbol}: duplicate dates")
    if not df.index.is_monotonic_increasing:
        problems.append(f"{symbol}: dates not monotonic increasing")
    if df[["open", "high", "low", "close"]].isna().any().any():
        problems.append(f"{symbol}: NaN in OHLC")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        problems.append(f"{symbol}: non-positive price present")
    bad_hl = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    )
    if bad_hl.any():
        problems.append(f"{symbol}: {int(bad_hl.sum())} rows violate high/low envelope")
    if (df["volume"] < 0).any():
        problems.append(f"{symbol}: negative volume")
    if len(df) < min_history:
        problems.append(f"{symbol}: insufficient history ({len(df)} < {min_history})")
    if max_future_date is not None and df.index.max() > max_future_date:
        problems.append(f"{symbol}: bars beyond expected last date ({df.index.max()})")
    span = (df.index.max() - df.index.min()).days
    if span > 0 and len(df) / (span / 365.25) > 265:
        problems.append(f"{symbol}: bar density implausible (>265 bars/yr)")
    gaps = df.index.to_series().diff().dt.days.dropna()
    if (gaps > 15).any():
        problems.append(f"{symbol}: {int((gaps > 15).sum())} calendar gaps > 15 days")
    return problems


def to_wide(frames: dict[str, pd.DataFrame], field: str = "close") -> pd.DataFrame:
    """dict[symbol, ohlcv frame] -> wide DataFrame of one field, union of dates."""
    if field not in ("open", "high", "low", "close", "volume"):
        raise ValueError(f"bad field: {field}")
    series = {sym: f[field] for sym, f in frames.items()}
    return pd.DataFrame(series).sort_index()
