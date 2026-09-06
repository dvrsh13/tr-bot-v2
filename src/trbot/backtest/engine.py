"""No-lookahead backtest engine.

Timeline discipline per rebalance date t:
  1. strategy sees data ≤ t (close of day t) -> proposes target weights
  2. risk engine approves (kill switch re-read; caps; drawdown gate)
  3. orders are diffed against current weights, chunked under the order cap
  4. fills execute at the OPEN of t+1 (slippage + commission)
  5. mark-to-market at the close of every day; HWM/drawdown updated daily

When the kill switch is triggered, open positions are force-closed at the next
open (protective de-risking is never blocked) and no new orders are taken.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trbot.backtest.metrics import compute_metrics
from trbot.config import Settings
from trbot.data.schema import to_wide
from trbot.execution.sim_broker import SimBroker
from trbot.portfolio import Fill, Portfolio
from trbot.risk import KillSwitch, RiskEngine
from trbot.strategies.base import Strategy, StrategyInput, build_strategy


@dataclass
class BacktestResult:
    equity: pd.Series
    weights: pd.DataFrame  # snapshots at each rebalance
    fills: list[Fill]
    decisions: list[tuple[pd.Timestamp, str]]
    kill_events: list[str]
    metrics: dict[str, float]
    benchmark: pd.Series


def _equal_weight_market_index(close: pd.DataFrame) -> pd.Series:
    """Equal-weight buy&hold index of the universe (market proxy for idio-vol)."""
    normed = close / close.iloc[0]
    return normed.mean(axis=1)


def run_backtest(
    frames: dict[str, pd.DataFrame], strategy: Strategy, settings: Settings, kill_switch: KillSwitch | None = None
) -> BacktestResult:
    wide_close = to_wide(frames, "close")
    wide_open = to_wide(frames, "open")
    returns = wide_close.pct_change()
    market_close = _equal_weight_market_index(wide_close)

    bt = settings.backtest
    warmup = bt.min_history_days
    if len(wide_close) <= warmup + 5:
        raise ValueError(f"not enough bars: {len(wide_close)} <= warmup {warmup}")

    pf = Portfolio(cash=bt.initial_capital)
    broker = SimBroker(settings)
    ks = kill_switch if kill_switch is not None else KillSwitch()
    risk = RiskEngine(settings, ks)
    # cooldown policy: after a kill, force-close, then auto-resume after
    # cooldown_days trading days (research semantics). Note: with a file-backed
    # kill switch this also clears the persisted file on resume.
    cooldown_mode = settings.risk.policy == "cooldown"
    cooldown_until_i: int | None = None

    equity_rows: list[float] = []
    equity_idx: list[pd.Timestamp] = []
    weight_rows: list[pd.Series] = []
    decisions: list[tuple[pd.Timestamp, str]] = []
    kill_events: list[str] = []
    turnover_rows: list[float] = []
    hwm = bt.initial_capital
    pending_orders: list[tuple[str, str, float]] = []

    for i in range(len(wide_close)):
        t = wide_close.index[i]

        # ---- morning: cooldown expiry (research semantics)
        if cooldown_mode and cooldown_until_i is not None and i >= cooldown_until_i and ks.is_triggered:
            ks.reset(confirm=True)
            # the de-risked book becomes the new baseline: the old HWM would
            # re-trigger the kill on the same close otherwise (kill-loop)
            hwm = equity_rows[-1] if equity_rows else hwm
            kill_events.append(f"{t.date()}: cooldown expired — trading resumed, HWM reset to {hwm:,.0f}")
            cooldown_until_i = None

        # ---- morning: fill orders decided at t-1, at today's open
        if pending_orders:
            fills = broker.execute(pending_orders, wide_open.iloc[i], t, pf)
            notional = sum(f.notional for f in fills)
            turnover_rows.append(notional / max(equity_rows[-1], 1e-9) if equity_rows else 0.0)
            pending_orders = []

        # ---- protective de-risking: kill switch -> force-close at open
        if ks.is_triggered and any(p.is_open for p in pf.positions.values()):
            closes = [(s, p.qty) for s, p in pf.positions.items() if p.is_open]
            pending_orders = []
            for sym, qty in closes:
                price = wide_open.iloc[i].get(sym)
                if pd.isna(price) or price <= 0:
                    continue
                pf.apply_fill(
                    Fill(
                        date=t,
                        symbol=sym,
                        side="sell",
                        qty=qty,
                        price=float(price) * (1 - broker.slippage_rate),
                        commission=float(price) * qty * broker.commission_rate,
                        notional=float(price) * qty,
                    )
                )
            if closes:
                kill_events.append(f"{t.date()}: force-closed {len(closes)} positions after kill")

        # ---- evening: mark to market
        eq = pf.equity(wide_close.iloc[i])
        equity_idx.append(t)
        equity_rows.append(eq)
        hwm = max(hwm, eq)

        if risk.check_drawdown(eq, hwm) and not ks.is_triggered:
            ks.trigger(f"drawdown {(eq / hwm - 1):.2%} breached -{settings.risk.max_drawdown_kill:.0%} threshold")
            kill_events.append(f"{t.date()}: kill switch triggered: {ks.reason}")
            if cooldown_mode:
                cooldown_until_i = i + max(settings.risk.cooldown_days_after_kill, 1)

        # ---- rebalance decision (data <= t only)
        is_rebalance = (i >= warmup) and ((i - warmup) % bt.rebalance_every == 0) and not ks.is_triggered
        if is_rebalance:
            snap = StrategyInput(
                close=wide_close.iloc[: i + 1], returns=returns.iloc[: i + 1], market_close=market_close.iloc[: i + 1]
            )
            try:
                proposed_row = strategy.target_weights(snap).iloc[-1]
            except Exception as e:  # noqa: BLE001 - strategy bugs fail closed, not forward
                decisions.append((t, f"strategy error: {e}"))
                continue
            proposed_row = proposed_row.reindex(wide_close.columns).fillna(0.0)
            decision = risk.approve(proposed_row, equity=eq, high_water_mark=hwm)
            decisions.append((t, decision.summary()))
            if decision.approved:
                current = pf.current_weights(wide_close.iloc[i], eq)
                pending_orders = broker.orders_from_weights(current, decision.weights, eq)
                weight_rows.append(decision.weights.rename(t))

    equity = pd.Series(equity_rows, index=equity_idx, name="equity")
    weights = pd.DataFrame(weight_rows) if weight_rows else pd.DataFrame()
    turnover = pd.Series(turnover_rows) if turnover_rows else None
    commissions = float(sum(f.commission for f in pf.fills))
    metrics = compute_metrics(equity, turnover=turnover, commissions=commissions)
    bench = _equal_weight_market_index(wide_close).loc[equity.index]
    benchmark = bench / bench.iloc[0] * bt.initial_capital
    return BacktestResult(
        equity=equity,
        weights=weights,
        fills=pf.fills,
        decisions=decisions,
        kill_events=kill_events,
        metrics=metrics,
        benchmark=benchmark,
    )


def run_strategy_backtest(
    frames: dict[str, pd.DataFrame], strategy_name: str, params: dict, settings: Settings
) -> BacktestResult:
    strategy = build_strategy(strategy_name, params)
    return run_backtest(frames, strategy, settings)
