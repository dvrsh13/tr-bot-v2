"""Data layer tests: standardization, validation, providers, universe."""

import numpy as np
import pandas as pd
import pytest

from trbot.data.providers import (
    AlpacaBarsProvider,
    ParquetProvider,
    SyntheticProvider,
)
from trbot.data.schema import repair_envelope, standardize_ohlcv, to_wide, validate_ohlcv
from trbot.data.universe import canonical, load_universe, provider_symbol_map


def _good_frame(days=300, start="2020-01-01", price=100.0):
    idx = pd.bdate_range(start, periods=days)
    rng = np.random.default_rng(1)
    close = price * np.exp(np.cumsum(rng.normal(0, 0.01, days)))
    open_ = close * (1 + rng.normal(0, 0.002, days))
    high = np.maximum(open_, close) * (1 + 0.005)
    low = np.minimum(open_, close) * (1 - 0.005)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": rng.integers(1e5, 1e6, days).astype(float)},
        index=idx,
    )


class TestStandardize:
    def test_renames_and_sorts(self):
        df = _good_frame(100).iloc[::-1].reset_index().rename(columns={"index": "date"})
        out = standardize_ohlcv(df)
        assert list(out.columns) == ["open", "high", "low", "close", "volume"]
        assert out.index.is_monotonic_increasing
        assert out.index.tz is None

    def test_dedupes_by_last(self):
        df = _good_frame(50)
        dup = pd.concat([df, df.iloc[[-1] * 3]])
        out = standardize_ohlcv(dup.reset_index().rename(columns={"index": "date"}))
        assert out.index.is_unique

    def test_missing_columns_rejected(self):
        with pytest.raises(ValueError, match="missing columns"):
            standardize_ohlcv(_good_frame(10)[["close", "volume"]].reset_index())

    def test_capitalized_columns_normalized(self):
        """Regression: Yahoo returns Capitalized columns — must still standardize."""
        df = _good_frame(100)
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        out = standardize_ohlcv(df)
        assert list(out.columns) == ["open", "high", "low", "close", "volume"]
        assert out.index.is_monotonic_increasing and out.index.is_unique


class TestValidation:
    def test_good_frame_passes(self):
        assert validate_ohlcv("X", _good_frame(300)) == []

    def test_envelope_violation(self):
        df = _good_frame(300)
        df.iloc[10, df.columns.get_loc("high")] = df.iloc[10]["low"] - 1
        problems = validate_ohlcv("X", df)
        assert any("envelope" in p for p in problems)

    def test_insufficient_history(self):
        problems = validate_ohlcv("X", _good_frame(50), min_history=60)
        assert any("insufficient" in p for p in problems)

    def test_nan_rejected(self):
        df = _good_frame(300)
        df.iloc[5, df.columns.get_loc("close")] = np.nan
        assert any("NaN" in p for p in validate_ohlcv("X", df))

    def test_gap_detection(self):
        df = _good_frame(300)
        df = df.drop(df.index[100:150])  # ~2-month calendar gap
        assert any("gaps" in p for p in validate_ohlcv("X", df))


class TestToWide:
    def test_union_of_dates(self):
        a, b = _good_frame(200), _good_frame(150)  # same start, B shorter
        wide = to_wide({"A": a, "B": b})
        assert len(wide) == 200
        assert wide["B"].iloc[-50:].isna().all()  # B missing the last 50 dates
        assert not wide["B"].iloc[:100].isna().any()


class TestSyntheticProvider:
    def test_deterministic_across_instances(self):
        syms = ["AAA", "BBB", "CCC"]
        f1 = SyntheticProvider(days=400, end=pd.Timestamp("2025-01-01")).load(syms)
        f2 = SyntheticProvider(days=400, end=pd.Timestamp("2025-01-01")).load(syms)
        for s in syms:
            pd.testing.assert_frame_equal(f1[s], f2[s])

    def test_different_symbols_differ(self):
        f = SyntheticProvider(days=400, end=pd.Timestamp("2025-01-01")).load(["AAA", "BBB"])
        assert not f["AAA"]["close"].equals(f["BBB"]["close"])

    def test_envelope_valid(self):
        f = SyntheticProvider(days=300, end=pd.Timestamp("2025-01-01")).load(["AAA"])["AAA"]
        assert validate_ohlcv("AAA", f) == []


class TestParquetProvider:
    def test_roundtrip(self, tmp_path):
        df = _good_frame(120)
        df.to_parquet(tmp_path / "AAA.parquet")
        prov = ParquetProvider(tmp_path)
        out = prov.load(["AAA"])
        pd.testing.assert_frame_equal(out["AAA"], standardize_ohlcv(df.reset_index().rename(columns={"index": "date"})))

    def test_missing_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ParquetProvider(tmp_path / "nope")


class TestAlpacaParse:
    """v1 live-fire lesson: /v2/stocks/bars returns bars keyed by SYMBOL."""

    PAYLOAD = {
        "bars": {
            "AAPL": [
                {
                    "t": "2024-01-02T05:00:00Z",
                    "o": 187.1,
                    "h": 188.4,
                    "l": 183.9,
                    "c": 185.6,
                    "v": 42650000,
                    "n": 500000,
                    "vw": 186.0,
                },
                {
                    "t": "2024-01-03T05:00:00Z",
                    "o": 184.2,
                    "h": 185.9,
                    "l": 183.4,
                    "c": 184.3,
                    "v": 41000000,
                    "n": 480000,
                    "vw": 184.8,
                },
            ],
            "MSFT": [],
        }
    }

    def test_dict_keyed_payload_parsed(self):
        frames = AlpacaBarsProvider.parse_bars_response(self.PAYLOAD)
        assert set(frames) == {"AAPL"}  # empty list for MSFT skipped
        df = frames["AAPL"]
        assert list(df.columns) == ["open", "high", "low", "close", "volume", "trades", "vwap"]
        assert df.index[0] == pd.Timestamp("2024-01-02")

    def test_list_payload_rejected(self):
        with pytest.raises(ValueError, match="dict keyed by symbol"):
            AlpacaBarsProvider.parse_bars_response({"bars": [{"t": "x"}]})

    def test_missing_bars_key_rejected(self):
        with pytest.raises(ValueError, match="missing 'bars'"):
            AlpacaBarsProvider.parse_bars_response({"data": {}})

    def test_batch_limit_enforced(self):
        prov = AlpacaBarsProvider.__new__(AlpacaBarsProvider)
        with pytest.raises(ValueError, match="<= 25"):
            prov.fetch_batch([f"S{i}" for i in range(26)])


class TestUniverse:
    def test_canonicalization(self):
        assert canonical("BRK-B") == "BRKB"
        assert canonical("brk.b") == "BRKB"

    def test_load_project_universe(self):
        members = load_universe("config/universe_us_core.csv")
        assert len(members) >= 30
        syms = {m.symbol for m in members}
        assert "BRKB" in syms
        brk = next(m for m in members if m.symbol == "BRKB")
        assert brk.yahoo_symbol == "BRK-B"
        assert brk.alpaca_symbol == "BRK.B"

    def test_duplicate_symbols_deduped(self, tmp_path):
        p = tmp_path / "u.csv"
        p.write_text("symbol,name,sector,yahoo_symbol,alpaca_symbol\nAAPL,Apple,T,AAPL,AAPL\nAAPL,Apple2,T,AAPL,AAPL\n")
        assert len(load_universe(p)) == 1

    def test_provider_symbol_map(self):
        members = load_universe("config/universe_us_core.csv")
        amap = provider_symbol_map(members, "alpaca")
        assert amap["BRKB"] == "BRK.B"
        ymap = provider_symbol_map(members, "yahoo")
        assert ymap["BRKB"] == "BRK-B"


class TestRepairEnvelope:
    def test_epsilon_artifact_fixed(self):
        df = _good_frame(100)
        df.iloc[5, df.columns.get_loc("low")] = df.iloc[5]["close"] + 1e-9
        assert any("envelope" in p for p in validate_ohlcv("X", df))
        fixed = repair_envelope(df)
        assert validate_ohlcv("X", fixed) == []

    def test_idempotent(self):
        df = repair_envelope(_good_frame(100))
        assert repair_envelope(df).equals(df)
