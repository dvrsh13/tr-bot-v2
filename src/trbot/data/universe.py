"""Universe definition + symbol normalization.

Canonical symbol form: uppercase, no separators (BRKB). Provider-specific
spellings live in the universe CSV columns (yahoo_symbol, alpaca_symbol) so the
same canonical name drives every data source.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UniverseMember:
    symbol: str  # canonical (no separators)
    name: str
    sector: str
    yahoo_symbol: str
    alpaca_symbol: str


def canonical(symbol: str) -> str:
    return symbol.replace(".", "").replace("-", "").replace("/", "").strip().upper()


def load_universe(path: str | Path, max_size: int = 0) -> list[UniverseMember]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"universe file not found: {p}")
    members: list[UniverseMember] = []
    seen: set[str] = set()
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            sym = canonical(row["symbol"])
            if not sym or sym in seen:
                continue
            seen.add(sym)
            members.append(
                UniverseMember(
                    symbol=sym,
                    name=row.get("name", sym),
                    sector=row.get("sector", "unknown"),
                    yahoo_symbol=row.get("yahoo_symbol", row["symbol"]),
                    alpaca_symbol=row.get("alpaca_symbol", row["symbol"]),
                )
            )
    if max_size and len(members) > max_size:
        raise ValueError(f"universe larger than allowed: {len(members)} > {max_size}")
    return members


def provider_symbol_map(members: list[UniverseMember], kind: str) -> dict[str, str]:
    """canonical -> provider-specific spelling (kind: yahoo | alpaca)."""
    col = {"yahoo": "yahoo_symbol", "alpaca": "alpaca_symbol"}[kind]
    return {m.symbol: getattr(m, col) for m in members}
