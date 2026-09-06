"""Fetch daily bars for the core universe from Yahoo Finance into the parquet cache.

Research-only acquisition path (the framework itself never depends on scraped
data — see INFRA-RESEARCH.md §2). Produces the same canonical parquet snapshots
that the Alpaca provider will produce once paper credentials exist, so the
strategy layer is provider-agnostic.

Usage: uv run python scripts/fetch_yahoo.py [--start 2019-01-01]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trbot.data.schema import repair_envelope, standardize_ohlcv, validate_ohlcv  # noqa: E402
from trbot.data.universe import load_universe, provider_symbol_map  # noqa: E402

CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"
UNIVERSE = Path(__file__).resolve().parents[1] / "config" / "universe_us_core.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    args = ap.parse_args()

    import yfinance as yf

    members = load_universe(UNIVERSE)
    ymap = provider_symbol_map(members, "yahoo")
    CACHE.mkdir(parents=True, exist_ok=True)

    print(f"fetching {len(members)} symbols from {args.start} ...")
    problems_all: dict[str, list[str]] = {}
    for i, m in enumerate(members):
        ys = ymap[m.symbol]
        for attempt in range(3):
            try:
                raw = yf.download(ys, start=args.start, auto_adjust=True, progress=False, multi_level_index=False)
                if raw is None or raw.empty:
                    raise ValueError("empty download")
                df = standardize_ohlcv(raw.reset_index())
                pre = validate_ohlcv(m.symbol, df, min_history=280)
                if any("envelope" in p for p in pre):
                    df = repair_envelope(df)  # upstream float-epsilon artifacts only
                # yfinance auto_adjust returns total-return-ish OHLC (split+div adjusted)
                problems = validate_ohlcv(m.symbol, df, min_history=280)
                problems_all[m.symbol] = problems
                df.to_parquet(CACHE / f"{m.symbol}.parquet")
                print(
                    f"  [{i + 1:2}/{len(members)}] {m.symbol:6} <- {ys:8} {len(df)} bars "
                    f"{df.index.min().date()}..{df.index.max().date()} "
                    f"{'OK' if not problems else 'PROBLEMS: ' + '; '.join(problems)}"
                )
                break
            except Exception as e:  # noqa: BLE001 - log and retry
                if attempt == 2:
                    problems_all[m.symbol] = [f"FETCH FAILED: {e}"]
                    print(f"  [{i + 1:2}/{len(members)}] {m.symbol:6} <- {ys:8} FAILED: {e}")
                else:
                    time.sleep(2 * (attempt + 1))
        time.sleep(0.8)

    failed = {s: p for s, p in problems_all.items() if p}
    print(f"\ndone: {len(problems_all) - len(failed)}/{len(problems_all)} clean, {len(failed)} with problems")
    for s, p in failed.items():
        print(f"  {s}: {'; '.join(p)}")
    return 1 if len(failed) > len(members) // 3 else 0


if __name__ == "__main__":
    raise SystemExit(main())
