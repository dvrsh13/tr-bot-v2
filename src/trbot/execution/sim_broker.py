"""Simulation broker: deterministic fills with cost model.

Fills happen at the next bar's open with slippage; commission is bps of
notional per side. Orders are chunked under the risk-engine order notional cap
(v1 convention): at most one capped chunk per (symbol, side, rebalance) — the
remainder converges on the next rebalance, which bounds daily churn.
"""

from __future__ import annotations

import math

import pandas as pd

from trbot.config import Settings
from trbot.portfolio import Fill, Portfolio


class SimBroker:
    def __init__(self, settings: Settings) -> None:
        self.commission_rate = settings.backtest.commission_bps / 1e4
        self.slippage_rate = settings.backtest.slippage_bps / 1e4
        self.order_cap_frac = settings.risk.order_notional_cap

    def orders_from_weights(
        self, current_w: pd.Series, target_w: pd.Series, equity: float, min_notional_frac: float = 0.002
    ) -> list[tuple[str, str, float]]:
        """Diff weights into (symbol, side, notional) orders; skip sub-noise trades."""
        symbols = sorted(set(current_w.index) | set(target_w.index))
        orders: list[tuple[str, str, float]] = []
        for sym in symbols:
            delta_w = float(target_w.get(sym, 0.0) - current_w.get(sym, 0.0))
            notional = delta_w * equity
            if abs(notional) < min_notional_frac * equity:
                continue
            side = "buy" if notional > 0 else "sell"
            capped = min(abs(notional), self.order_cap_frac * equity)
            orders.append((sym, side, capped))
        return orders

    def execute(
        self, orders: list[tuple[str, str, float]], open_prices: pd.Series, date: pd.Timestamp, pf: Portfolio
    ) -> list[Fill]:
        """Fill orders at open_prices (the bar AFTER the decision date)."""
        fills: list[Fill] = []
        for sym, side, notional in orders:
            if sym not in open_prices.index or pd.isna(open_prices[sym]) or open_prices[sym] <= 0:
                continue  # no tradable price that morning: order lapses
            raw_price = float(open_prices[sym])
            price = raw_price * (1 + self.slippage_rate) if side == "buy" else raw_price * (1 - self.slippage_rate)
            qty = notional / price
            if not math.isfinite(qty) or qty <= 0:
                continue
            commission = notional * self.commission_rate
            fill = Fill(
                date=date, symbol=sym, side=side, qty=qty, price=price, commission=commission, notional=notional
            )
            pf.apply_fill(fill)
            fills.append(fill)
        return fills
