"""Alpaca paper-trading adapter (stdlib REST, no SDK).

Security contract (ported from v1):
- endpoint allowlist is a CODE-LEVEL constant; configuration cannot extend it;
- URLs containing live/prod/real are refused outright;
- order submission is double-gated (config flag AND TRBOT_ORDERS_ENABLED=true);
- credentials come from the environment only.

Transport is injectable so tests can exercise every path without network.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable

from trbot.config import BrokerConfig, Settings

# (base_url, method, path-template) — the complete set of reachable endpoints.
ALLOWLIST: set[tuple[str, str, str]] = {
    ("https://paper-api.alpaca.markets", "GET", "/v2/account"),
    ("https://paper-api.alpaca.markets", "GET", "/v2/positions"),
    ("https://paper-api.alpaca.markets", "GET", "/v2/orders"),
    ("https://paper-api.alpaca.markets", "POST", "/v2/orders"),
    ("https://paper-api.alpaca.markets", "DELETE", "/v2/orders/{order_id}"),
    ("https://data.alpaca.markets", "GET", "/v2/stocks/bars"),
}


class AlpacaError(RuntimeError):
    pass


class AlpacaPaperBroker:
    def __init__(
        self, settings: Settings, transport: Callable[[urllib.request.Request], tuple[int, bytes]] | None = None
    ) -> None:
        if settings.mode is not None:
            pass  # mode checked by callers; adapter itself is inert without gates
        self.settings = settings
        self.broker: BrokerConfig = settings.broker
        self._transport = transport or self._urlopen_transport

    @staticmethod
    def _urlopen_transport(req: urllib.request.Request) -> tuple[int, bytes]:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - allowlisted hosts only
            return resp.status, resp.read()

    def _assert_allowed(self, base: str, method: str, path: str) -> None:
        low = (base + path).lower()
        if "live" in low or "prod" in low or "real" in low:
            raise AlpacaError(f"refusing non-paper endpoint: {base}{path}")
        if (base, method, path) not in ALLOWLIST:
            raise AlpacaError(f"endpoint not in allowlist: {method} {base}{path}")

    def _request(self, method: str, path: str, body: dict | None = None, base: str | None = None) -> dict | list:
        base = base or self.broker.base_url
        self._assert_allowed(base, method, path)
        key_id = _env(self.broker.key_id_env)
        secret = _env(self.broker.secret_env)
        if not key_id or not secret:
            raise AlpacaError(f"missing credentials: {self.broker.key_id_env}/{self.broker.secret_env}")
        req = urllib.request.Request(
            base + path,
            method=method,
            headers={
                "APCA-API-KEY-ID": key_id,
                "APCA-API-SECRET-KEY": secret,
                "Content-Type": "application/json",
            },
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            status, raw = self._transport(req)
        except urllib.error.HTTPError as e:
            raise AlpacaError(f"alpaca {method} {path} -> HTTP {e.code}: {e.read()[:200]!r}") from e
        if status >= 400:
            raise AlpacaError(f"alpaca {method} {path} -> HTTP {status}")
        return json.loads(raw.decode()) if raw else {}

    # ---- trading endpoints ----------------------------------------------------
    def get_account(self) -> dict:
        return self._request("GET", "/v2/account")

    def get_positions(self) -> list[dict]:
        out = self._request("GET", "/v2/positions")
        return out if isinstance(out, list) else []

    def get_orders(self, status: str = "open") -> list[dict]:
        return self._request("GET", f"/v2/orders?status={status}&limit=100")

    def submit_order(self, *, symbol: str, qty: float, side: str, client_order_id: str) -> dict:
        if side not in ("buy", "sell"):
            raise AlpacaError(f"bad side: {side}")
        if not self.settings.orders_actually_enabled:
            raise AlpacaError(
                "order submission blocked: double-gate not open "
                "(config orders.enabled AND env TRBOT_ORDERS_ENABLED=true required)"
            )
        body = {
            "symbol": symbol,
            "qty": f"{qty:.4f}",
            "side": side,
            "type": "market",
            "time_in_force": "day",
            "client_order_id": client_order_id,
        }
        return self._request("POST", "/v2/orders", body)

    def cancel_order(self, order_id: str) -> None:
        self._request("DELETE", f"/v2/orders/{order_id}")


def _env(name: str) -> str:
    import os

    return os.environ.get(name, "")


def make_order_claim_id(trade_date: str, symbol: str, side: str) -> str:
    """Deterministic client_order_id per (date, symbol, side) — v1 convention:
    qty excluded so at most one order per (symbol, side, day) bounds churn."""
    return f"trbot-{trade_date}-{symbol}-{side}".lower().replace(".", "")
