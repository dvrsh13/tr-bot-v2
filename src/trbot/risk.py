"""Risk engine + persistent kill switch.

Authority chain (ported from v1): strategies PROPOSE target weights, the risk
engine APPROVES by issuing a RiskDecision, the broker/executer consumes only
stamped weights. No code path reaches execution without passing through here.
The kill switch is re-read before every approval; when triggered, everything is
rejected. Kill-switch state is fail-safe: a corrupt file counts as TRIGGERED.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from trbot.config import Settings


@dataclass
class KillSwitch:
    """Persistent, fail-safe kill switch. File-backed when path is given."""

    path: Path | None = None
    _triggered: bool = False
    _reason: str = ""

    def _load(self) -> tuple[bool, str]:
        if self.path is None or not self.path.exists():
            return self._triggered, self._reason
        try:
            data = json.loads(self.path.read_text())
            return bool(data.get("triggered", False)), str(data.get("reason", ""))
        except (json.JSONDecodeError, OSError):
            return True, "corrupt kill-switch file (fail-safe triggered)"

    @property
    def is_triggered(self) -> bool:
        triggered, reason = self._load()
        self._triggered, self._reason = triggered, reason
        return triggered

    @property
    def reason(self) -> str:
        return self._reason

    def trigger(self, reason: str) -> None:
        self._triggered = True
        self._reason = reason
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"triggered": True, "reason": reason, "triggered_at": pd.Timestamp.now().isoformat()})
            )

    def reset(self, *, confirm: bool = False) -> None:
        """Manual-only reset. Silent resets are refused."""
        if not confirm:
            raise PermissionError("kill switch reset requires confirm=True (manual operation)")
        self._triggered = False
        self._reason = ""
        if self.path is not None and self.path.exists():
            self.path.unlink()


@dataclass
class RiskDecision:
    """The stamp that authorizes execution of specific weights."""

    approved: bool
    weights: pd.Series
    checks: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        status = "APPROVED" if self.approved else "REJECTED"
        reasons = "; ".join(f"{k}={v}" for k, v in self.checks.items())
        return f"[{status}] {reasons or 'ok'}"


class RiskEngine:
    """Ordered checks on proposed weights. Fails closed: anything suspicious
    (NaN, infinite, negative) rejects the whole proposal."""

    def __init__(self, settings: Settings, kill_switch: KillSwitch | None = None) -> None:
        self.cfg = settings.risk
        self.bt = settings.backtest
        self.kill_switch = kill_switch or KillSwitch()

    def check_drawdown(self, equity: float, high_water_mark: float) -> bool:
        """True if drawdown breach — caller triggers the kill switch."""
        if high_water_mark <= 0:
            return False
        return (equity / high_water_mark - 1) <= -self.cfg.max_drawdown_kill

    def approve(self, proposed: pd.Series, *, equity: float, high_water_mark: float) -> RiskDecision:
        checks: dict[str, str] = {}
        # finite + non-negative gate on RAW values first — fillna must never
        # launder NaN into silent zeros (v1 lesson)
        if len(proposed) and not all(
            (x is None) is False and math.isfinite(float(x)) and float(x) >= 0 for x in proposed.values
        ):
            bad = [
                s
                for s, x in proposed.items()
                if not (isinstance(x, (int, float)) and math.isfinite(float(x)) and float(x) >= 0)
            ]
            return RiskDecision(False, proposed.fillna(0.0) * 0.0, {"finite_nonneg": f"bad weights for {bad}"})
        w = proposed.fillna(0.0)

        if self.kill_switch.is_triggered:
            return RiskDecision(False, w * 0.0, {"kill_switch": f"triggered: {self.kill_switch.reason}"})

        active = w[w > 1e-9]
        scaled_note = ""

        if self.cfg.on_violation == "scale":
            # research mode: cap-and-renormalize instead of rejecting. Garbage
            # (NaN/inf/negative) is still rejected above — never laundered.
            if len(active) > self.bt.max_positions:
                keep = active.sort_values(ascending=False).index[: self.bt.max_positions]
                w = w.where(w.index.isin(keep), 0.0)
                active = w[w > 1e-9]
                scaled_note += f"trimmed>{self.bt.max_positions};"
            if (active > self.bt.max_position_weight + 1e-9).any():
                w = w.clip(upper=self.bt.max_position_weight)
                active = w[w > 1e-9]
                scaled_note += f"capped@{self.bt.max_position_weight};"
            gross = float(active.sum())
            if gross > self.bt.max_gross_exposure + 1e-6:
                w = w * (self.bt.max_gross_exposure / gross)
                active = w[w > 1e-9]
                gross = float(active.sum())
                scaled_note += f"scaled_to_gross{self.bt.max_gross_exposure};"
            if scaled_note:
                return RiskDecision(True, w, {"ok": f"scaled [{scaled_note}] gross {gross:.3f}"})
            checks["ok"] = f"approved {len(active)} positions, gross {gross:.3f}"
            return RiskDecision(True, w, checks)

        if len(active) > self.bt.max_positions:
            return RiskDecision(False, w * 0.0, {"max_positions": f"{len(active)} > {self.bt.max_positions}"})
        if (active > self.bt.max_position_weight + 1e-9).any():
            worst = active.idxmax()
            return RiskDecision(False, w * 0.0, {"max_position_weight": f"{worst}={active.max():.3f}"})
        gross = float(active.sum())
        if gross > self.bt.max_gross_exposure + 1e-6:
            return RiskDecision(False, w * 0.0, {"max_gross": f"{gross:.3f} > {self.bt.max_gross_exposure}"})

        if self.check_drawdown(equity, high_water_mark):
            self.kill_switch.trigger(
                f"drawdown {(equity / high_water_mark - 1):.2%} breached -{self.cfg.max_drawdown_kill:.0%} threshold"
            )
            return RiskDecision(False, w * 0.0, {"drawdown_kill": self.kill_switch.reason})

        checks["ok"] = f"approved {len(active)} positions, gross {gross:.3f}"
        return RiskDecision(True, w, checks)
