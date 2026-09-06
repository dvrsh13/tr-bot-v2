"""Trial ledger: append-only record of every backtest configuration tried.

Methodology mandate (Harvey-Liu-Zhu 2016; Bailey et al. 2014/2017): the number
of trials is the raw material of backtest overfitting. Any sweep/optimization
must go through this ledger so the multiple-testing burden is measurable and
PBO can be estimated over recorded trials.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def dataset_fingerprint(frames: dict[str, pd.DataFrame]) -> str:
    """Stable content fingerprint of a dataset (symbol set + shape + last close)."""
    h = hashlib.sha256()
    for sym in sorted(frames):
        df = frames[sym]
        h.update(f"{sym}|{len(df)}|{df.index.min()}|{df.index.max()}|{df['close'].iloc[-1]:.6f}".encode())
        h.update(zlib.crc32(df["close"].to_numpy().tobytes()).to_bytes(4, "big"))
    return h.hexdigest()[:16]


def config_hash(strategy: str, params: dict) -> str:
    blob = json.dumps({"strategy": strategy, "params": params}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


class TrialLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, *, strategy: str, params: dict, dataset: str, metrics: dict, source: str = "manual") -> int:
        trial_id = self.count() + 1
        entry = {
            "trial_id": trial_id,
            "recorded_at": datetime.now(UTC).isoformat(),
            "strategy": strategy,
            "params": params,
            "config_hash": config_hash(strategy, params),
            "dataset": dataset,
            "metrics": {
                k: (round(v, 6) if isinstance(v, float) else v)
                for k, v in metrics.items()
                if isinstance(v, (int, float, str))
            },
            "source": source,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        return trial_id

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def count(self) -> int:
        return len(self.load())

    def for_dataset(self, dataset: str) -> list[dict]:
        return [t for t in self.load() if t.get("dataset") == dataset]
