"""trbot CLI — backtest, validate, walk-forward, sweep (with PBO), trials."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

from trbot.backtest.engine import run_strategy_backtest
from trbot.config import load_settings
from trbot.data.providers import build_provider
from trbot.data.schema import validate_ohlcv
from trbot.data.universe import load_universe
from trbot.research.pbo import pbo_from_configs
from trbot.research.trial_ledger import TrialLedger, dataset_fingerprint
from trbot.research.walkforward import walk_forward
from trbot.strategies.base import REGISTRY

console = Console()
LEDGER = Path("state/trials.jsonl")
PLOTS = Path("reports/plots")


def _load_frames(settings):
    members = load_universe(settings.data.universe_path)
    symbols = [m.symbol for m in members]
    provider = build_provider(settings.data)
    frames = provider.load(symbols)
    if not frames:
        console.print(
            f"[red]no data loaded for {len(symbols)} symbols from "
            f"provider={settings.data.provider} ({settings.data.cache_dir})[/red]"
        )
        sys.exit(4)
    return members, frames


def _print_metrics(metrics: dict, title: str) -> None:
    t = Table(title=title)
    t.add_column("metric")
    t.add_column("value", justify="right")
    fmt = {
        "total_return": "+.2%",
        "cagr": "+.2%",
        "ann_vol": ".2%",
        "sharpe": ".2f",
        "sortino": ".2f",
        "max_drawdown": ".2%",
        "calmar": ".2f",
        "win_rate_daily": ".1%",
        "turnover_ann": ".1f",
        "commissions_total": ",.0f",
    }
    for k, v in metrics.items():
        f = fmt.get(k, "")
        t.add_row(k, format(v, f) if f and isinstance(v, (int, float)) else str(v))
    console.print(t)


def cmd_backtest(args) -> int:
    overrides: dict = {"strategy": {"name": args.strategy, "params": {}}}
    if args.config:
        overrides = {}
    settings = load_settings(args.config, overrides=overrides)
    if args.strategy:
        settings.strategy.name = args.strategy
    for kv in args.param or []:
        k, v = kv.split("=", 1)
        try:
            settings.strategy.params[k] = int(v)
        except ValueError:
            try:
                settings.strategy.params[k] = float(v)
            except ValueError:
                settings.strategy.params[k] = v
    members, frames = _load_frames(settings)
    dataset = dataset_fingerprint(frames)
    res = run_strategy_backtest(frames, settings.strategy.name, settings.strategy.params, settings)
    _print_metrics(
        res.metrics, f"{settings.strategy.name} {settings.strategy.params or ''} | {len(frames)} symbols | ds={dataset}"
    )
    if res.kill_events:
        console.print(f"[yellow]kill events:[/yellow] {res.kill_events}")
    if args.plot:
        PLOTS.mkdir(parents=True, exist_ok=True)
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))
        (res.equity / res.equity.iloc[0]).plot(ax=ax, label="strategy")
        (res.benchmark / res.benchmark.iloc[0]).plot(ax=ax, label="equal-weight universe", alpha=0.7)
        ax.set_title(f"{settings.strategy.name} vs universe")
        ax.legend()
        fig.tight_layout()
        suffix = "_".join(f"{k}{v}" for k, v in sorted(settings.strategy.params.items()))[:40]
        out = PLOTS / f"{settings.strategy.name}_{suffix or 'default'}.png"
        fig.savefig(out, dpi=120)
        console.print(f"plot -> {out}")
    if not args.no_ledger:
        led = TrialLedger(LEDGER)
        tid = led.record(
            strategy=settings.strategy.name,
            params=settings.strategy.params,
            dataset=dataset,
            metrics=res.metrics,
            source="cli",
        )
        console.print(f"[dim]trial #{tid} recorded -> {LEDGER}[/dim]")
    return 0


def cmd_validate(args) -> int:
    settings = load_settings(args.config)
    members, frames = _load_frames(settings)
    problems = {}
    for m in members:
        if m.symbol in frames:
            p = validate_ohlcv(m.symbol, frames[m.symbol], min_history=settings.backtest.min_history_days)
            if p:
                problems[m.symbol] = p
    console.print(f"[green]{len(frames)}/{len(members)} symbols loaded[/green]; {len(problems)} with problems")
    for s, p in problems.items():
        console.print(f"  [yellow]{s}[/yellow]: {'; '.join(p)}")
    wide_dates = (min(f.index.min() for f in frames.values()), max(f.index.max() for f in frames.values()))
    console.print(f"date span: {wide_dates[0].date()} .. {wide_dates[1].date()}")
    return 0 if not problems else 1


def cmd_walkforward(args) -> int:
    settings = load_settings(args.config)
    settings.strategy.name = args.strategy or settings.strategy.name
    for kv in args.param or []:
        k, v = kv.split("=", 1)
        settings.strategy.params[k] = int(v) if v.isdigit() else v
    _, frames = _load_frames(settings)
    strat_name = settings.strategy.name
    from trbot.strategies.base import build_strategy

    res = walk_forward(frames, build_strategy(strat_name, settings.strategy.params), settings, n_folds=args.folds)
    t = Table(title=f"walk-forward {strat_name} {settings.strategy.params or ''}")
    for c in ("fold", "start", "end", "oos_return", "oos_sharpe", "max_dd"):
        t.add_column(c)
    for f in res.folds:
        t.add_row(
            str(f.fold),
            str(f.start.date()),
            str(f.end.date()),
            f"{f.oos_return:+.2%}",
            f"{f.oos_sharpe:.2f}",
            f"{f.max_drawdown:.2%}",
        )
    console.print(t)
    console.print(res.summary())
    led = TrialLedger(LEDGER)
    led.record(
        strategy=strat_name,
        params={"wf": args.folds, **settings.strategy.params},
        dataset=dataset_fingerprint(frames),
        metrics={"oos_return_total": res.aggregate["oos_return_total"], "oos_sharpe": res.aggregate["oos_sharpe"]},
        source="walkforward",
    )
    return 0


def cmd_sweep(args) -> int:
    settings = load_settings(args.config)
    settings.strategy.name = args.strategy
    grid_spec = json.loads(Path(args.grid).read_text()) if Path(args.grid).exists() else json.loads(args.grid)
    keys = list(grid_spec)
    import itertools

    combos = [dict(zip(keys, vals, strict=False)) for vals in itertools.product(*(grid_spec[k] for k in keys))]
    console.print(f"sweep {args.strategy}: {len(combos)} configs {grid_spec}")
    res = pbo_from_configs(_frames_only(settings), args.strategy, combos, settings, n_blocks=args.blocks)
    t = Table(title="per-config OOS Sharpe (full period)")
    t.add_column("config")
    t.add_column("oos sharpe", justify="right")
    for k, v in sorted(res.per_config_oos_sharpe.items(), key=lambda kv: -kv[1]):
        t.add_row(k, f"{v:.2f}")
    console.print(t)
    console.print(f"[bold]PBO:[/bold] {res.summary()}")
    led = TrialLedger(LEDGER)
    _, frames = _load_frames(settings)
    ds = dataset_fingerprint(frames)
    for combo in combos:
        led.record(strategy=args.strategy, params=combo, dataset=ds, metrics={}, source="sweep")
    led.record(strategy=args.strategy, params={"pbo_grid": combos}, dataset=ds, metrics={"pbo": res.pbo}, source="pbo")
    console.print(f"[dim]{len(combos) + 1} trials recorded -> {LEDGER}[/dim]")
    return 0


def _frames_only(settings):
    _, frames = _load_frames(settings)
    return frames


def cmd_trials(args) -> int:
    led = TrialLedger(LEDGER)
    entries = led.load()
    console.print(f"{len(entries)} trials recorded")
    t = Table()
    for c in ("#", "strategy", "params", "dataset", "sharpe", "source"):
        t.add_column(c)
    for e in entries[-args.last :]:
        t.add_row(
            str(e["trial_id"]),
            e["strategy"],
            json.dumps(e["params"])[:40],
            e["dataset"][:8],
            str(e["metrics"].get("sharpe", "-")),
            e["source"],
        )
    console.print(t)
    return 0


def cmd_selftest(args) -> int:
    """Engine sanity on deterministic synthetic data — no cache needed."""
    from trbot.config import Settings
    from trbot.data.providers import SyntheticProvider

    settings = Settings.model_validate(
        {
            "backtest": {"min_history_days": 280, "rebalance_every": 21},
            "strategy": {"name": "xs_momentum", "params": {"top_n": 10}},  # 0.1/name <= 0.15 cap
        }
    )
    frames = SyntheticProvider(days=900, end=pd.Timestamp("2025-06-30")).load([f"S{i}" for i in range(10)])
    res = run_strategy_backtest(frames, "xs_momentum", {"top_n": 10}, settings)
    ok = len(res.equity) == 900 and res.metrics and res.fills
    console.print(
        f"selftest: {'[green]PASS[/green]' if ok else '[red]FAIL[/red]'} "
        f"({res.metrics.get('sharpe', float('nan')):.2f} sharpe, "
        f"{res.metrics.get('total_return', 0):+.2%} return)"
    )
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="trbot", description="tr-bot-v2 paper trading framework")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("backtest", help="run a backtest")
    p.add_argument("--config", default="config/default.yaml")
    p.add_argument("--strategy", default=None, choices=sorted(REGISTRY))
    p.add_argument("--param", action="append", help="k=v strategy param, repeatable")
    p.add_argument("--plot", action="store_true")
    p.add_argument("--no-ledger", action="store_true")
    p.set_defaults(fn=cmd_backtest)

    p = sub.add_parser("validate-data", help="validate cached data")
    p.add_argument("--config", default="config/default.yaml")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("walkforward", help="walk-forward validation")
    p.add_argument("--config", default="config/default.yaml")
    p.add_argument("--strategy", default=None, choices=sorted(REGISTRY))
    p.add_argument("--param", action="append")
    p.add_argument("--folds", type=int, default=4)
    p.set_defaults(fn=cmd_walkforward)

    p = sub.add_parser("sweep", help="parameter sweep + PBO")
    p.add_argument("--config", default="config/default.yaml")
    p.add_argument("--strategy", required=True, choices=sorted(REGISTRY))
    p.add_argument("--grid", required=True, help="JSON grid, e.g. '{\"top_n\":[3,5,8]}' or path")
    p.add_argument("--blocks", type=int, default=8)
    p.set_defaults(fn=cmd_sweep)

    p = sub.add_parser("trials", help="show trial ledger")
    p.add_argument("--last", type=int, default=20)
    p.set_defaults(fn=cmd_trials)

    p = sub.add_parser("selftest", help="synthetic-data engine sanity")
    p.set_defaults(fn=cmd_selftest)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
