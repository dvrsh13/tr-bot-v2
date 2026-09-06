"""Portfolio ledger: cash, positions, fills, realized PnL (net of costs)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Fill:
    date: pd.Timestamp
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    price: float  # actual fill price (after slippage)
    commission: float
    notional: float

    def __post_init__(self) -> None:
        if self.side not in ("buy", "sell"):
            raise ValueError(f"bad side: {self.side}")
        if self.qty <= 0 or not pd.notna(self.qty):
            raise ValueError(f"bad qty: {self.qty}")


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_cost: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.qty > 1e-9


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)
    realized_pnl: float = 0.0

    def market_value(self, prices: pd.Series) -> float:
        total = 0.0
        for sym, pos in self.positions.items():
            if pos.is_open and sym in prices.index and pd.notna(prices[sym]):
                total += pos.qty * float(prices[sym])
        return total

    def equity(self, prices: pd.Series) -> float:
        return self.cash + self.market_value(prices)

    def apply_fill(self, fill: Fill) -> None:
        """Apply a fill to cash/positions. Realized PnL is net of commissions."""
        pos = self.positions.setdefault(fill.symbol, Position(fill.symbol))
        if fill.side == "buy":
            total_cost = pos.avg_cost * pos.qty + fill.notional + fill.commission
            pos.qty += fill.qty
            pos.avg_cost = total_cost / pos.qty if pos.qty > 1e-12 else 0.0
            self.cash -= fill.notional + fill.commission
        else:
            sell_qty = min(fill.qty, pos.qty)
            cost_basis = pos.avg_cost * sell_qty
            self.realized_pnl += (fill.notional - fill.commission) - cost_basis
            self.cash += fill.notional - fill.commission
            pos.qty -= sell_qty
            if pos.qty <= 1e-9:
                pos.qty = 0.0
                pos.avg_cost = 0.0
        self.fills.append(fill)

    def current_weights(self, prices: pd.Series, equity: float) -> pd.Series:
        if equity <= 0:
            return pd.Series(dtype="float64")
        mv = {sym: pos.qty * float(prices.get(sym, float("nan"))) for sym, pos in self.positions.items() if pos.is_open}
        return pd.Series({s: v / equity for s, v in mv.items() if pd.notna(v)})
