"""Paper runner: ONE trading cycle then exit, fail-closed.

Exit codes (v1 convention):
  0 success (or read-only plan when orders are gated off)
  2 missing credentials
  3 state store unreachable
  4 data unavailable/invalid
  5 reconciliation failure
  6 broker error

In PAPER mode with both order gates open it submits orders; otherwise it runs a
full read-only cycle and emits the order plan it WOULD have executed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from trbot.config import Settings, load_settings
from trbot.data.providers import AlpacaBarsProvider
from trbot.data.universe import load_universe, provider_symbol_map
from trbot.execution.alpaca_paper import AlpacaPaperBroker, make_order_claim_id
from trbot.risk import KillSwitch, RiskEngine
from trbot.state import StateStore
from trbot.strategies.base import build_strategy


@dataclass
class CyclePlan:
    date: str
    targets: dict[str, float] = field(default_factory=dict)
    orders: list[dict] = field(default_factory=list)
    submitted: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def run_paper_cycle(
    settings: Settings, state: StateStore, kill_switch: KillSwitch | None = None
) -> tuple[int, CyclePlan]:
    run_id = state.start_run(settings.mode.value)
    plan = CyclePlan(date=pd.Timestamp.now().strftime("%Y-%m-%d"))
    ks = kill_switch or KillSwitch()

    def finish(code: int, status: str, note: str = "") -> tuple[int, CyclePlan]:
        state.finish_run(run_id, status, code, note)
        state.audit("cycle_finish", f"{status} exit={code} {note}")
        return code, plan

    # 1) kill switch first — a halted bot must not spend API calls
    if ks.is_triggered:
        return finish(0, "halted", f"kill switch active: {ks.reason}")

    # 2) credentials (fail closed before anything else)
    import os

    key_id = os.environ.get(settings.broker.key_id_env, "")
    secret = os.environ.get(settings.broker.secret_env, "")
    if not key_id or not secret:
        plan.notes.append(f"missing {settings.broker.key_id_env}/{settings.broker.secret_env}")
        return finish(2, "failed", "missing credentials")

    # 3) data
    members = load_universe(settings.data.universe_path)
    smap = provider_symbol_map(members, "alpaca")
    provider = AlpacaBarsProvider(settings.broker, start=settings.data.start, end=settings.data.end)
    try:
        frames = {}
        for i in range(0, len(members), 25):
            batch = [smap[m.symbol] for m in members[i : i + 25]]
            for canonical_sym, df in provider.fetch_batch(batch).items():
                frames[canonical_sym] = df
    except Exception as e:  # noqa: BLE001
        plan.notes.append(f"data failure: {e}")
        return finish(4, "failed", f"data: {e}")
    if not frames:
        return finish(4, "failed", "no data returned")

    # 4) strategy targets from full history (runner runs after the close)
    try:
        from trbot.data.schema import to_wide

        wide_close = to_wide(frames, "close")
        returns = wide_close.pct_change()
        market = (wide_close / wide_close.iloc[0]).mean(axis=1)
        from trbot.strategies.base import StrategyInput

        snap = StrategyInput(close=wide_close, returns=returns, market_close=market)
        targets = (
            build_strategy(settings.strategy.name, settings.strategy.params).target_weights(snap).iloc[-1].fillna(0.0)
        )
    except Exception as e:  # noqa: BLE001
        plan.notes.append(f"strategy failure: {e}")
        return finish(4, "failed", f"strategy: {e}")

    # 5) risk approval (kill switch re-read)
    account_equity = float(state.last_equity() or settings.backtest.initial_capital)
    risk = RiskEngine(settings, ks)
    decision = risk.approve(
        targets, equity=account_equity, high_water_mark=max(account_equity, settings.backtest.initial_capital)
    )
    state.audit("risk_decision", decision.summary())
    if not decision.approved:
        plan.notes.append(f"risk rejected: {decision.summary()}")
        if ks.is_triggered:
            return finish(0, "halted", "kill switch active")
        plan.targets = {k: float(v) for k, v in targets.items()}
        return finish(0, "planned", "risk rejected; read-only plan emitted")

    plan.targets = {k: float(v) for k, v in decision.weights.items() if v > 1e-9}

    # 6) order plan (no positions endpoint in v0 runner: deltas vs empty book,
    #    bounded by the order cap; reconciliation arrives with position sync)
    broker = AlpacaPaperBroker(settings)
    order_cap = settings.risk.order_notional_cap
    for sym, w in sorted(plan.targets.items()):
        notional = min(w * account_equity, order_cap * account_equity)
        if notional < settings.backtest.initial_capital * 0.002:
            continue
        side = "buy"
        claim_id = make_order_claim_id(plan.date, sym, side)
        plan.orders.append({"symbol": sym, "side": side, "notional": notional, "claim_id": claim_id})

    # 7) submission — only when both gates are open
    if not settings.orders_actually_enabled:
        plan.notes.append(f"orders gated off: read-only plan with {len(plan.orders)} orders")
        return finish(0, "planned", "read-only cycle")

    for order in plan.orders:
        if not state.claim_order(order["claim_id"], order["symbol"], order["side"], plan.date):
            plan.notes.append(f"duplicate claim skipped: {order['claim_id']}")
            continue
        try:
            qty = order["notional"] / _last_price(frames, order["symbol"])
            resp = broker.submit_order(
                symbol=order["symbol"], qty=qty, side=order["side"], client_order_id=order["claim_id"]
            )
            order["broker_id"] = resp.get("id", "")
            plan.submitted.append(order)
            state.audit("order_submitted", f"{order['symbol']} {order['side']} qty={qty:.4f}")
        except Exception as e:  # noqa: BLE001
            plan.notes.append(f"broker error on {order['symbol']}: {e}")
            return finish(6, "failed", f"broker: {e}")

    return finish(0, "ok", f"submitted {len(plan.submitted)} orders")


def _last_price(frames: dict[str, pd.DataFrame], alpaca_symbol: str) -> float:
    df = frames.get(alpaca_symbol)
    if df is None or df.empty:
        raise RuntimeError(f"no price for {alpaca_symbol}")
    px = float(df["close"].iloc[-1])
    if px <= 0:
        raise RuntimeError(f"bad price for {alpaca_symbol}: {px}")
    return px


def main(argv: list[str] | None = None) -> int:
    cfg_path = None
    if argv and argv[0] == "--config":
        cfg_path = argv[1]
    settings = load_settings(cfg_path, overrides={"mode": "paper"})
    state = StateStore(Path("state/trbot.db"))
    try:
        code, _plan = run_paper_cycle(settings, state)
    except Exception as e:  # noqa: BLE001 — fail closed, print, nonzero exit
        print(f"cycle crashed: {e}", file=sys.stderr)
        return 6
    finally:
        state.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
