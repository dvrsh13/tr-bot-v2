"""Risk engine, kill switch, portfolio, sim broker tests."""

from __future__ import annotations

import pandas as pd
import pytest

from trbot.execution.sim_broker import SimBroker
from trbot.portfolio import Fill, Portfolio
from trbot.risk import KillSwitch, RiskEngine


def _w(**weights):
    return pd.Series(weights, dtype="float64")


class TestKillSwitch:
    def test_persist_and_reload(self, tmp_path):
        p = tmp_path / "kill.json"
        ks = KillSwitch(path=p)
        assert not ks.is_triggered
        ks.trigger("test breach")
        assert ks.is_triggered
        ks2 = KillSwitch(path=p)  # fresh instance sees persisted state
        assert ks2.is_triggered and "test breach" in ks2.reason

    def test_corrupt_file_failsafe(self, tmp_path):
        p = tmp_path / "kill.json"
        p.write_text("{not json at all")
        ks = KillSwitch(path=p)
        assert ks.is_triggered
        assert "corrupt" in ks.reason

    def test_reset_requires_confirm(self, tmp_path):
        ks = KillSwitch(path=tmp_path / "kill.json")
        ks.trigger("x")
        with pytest.raises(PermissionError):
            ks.reset()
        ks.reset(confirm=True)
        assert not ks.is_triggered

    def test_missing_file_ok(self, tmp_path):
        assert not KillSwitch(path=tmp_path / "absent.json").is_triggered


@pytest.fixture
def engine(sim_settings):
    return RiskEngine(sim_settings)


class TestRiskEngine:
    def test_approves_sane_weights(self, engine):
        d = engine.approve(_w(a=0.1, b=0.1), equity=100_000, high_water_mark=100_000)
        assert d.approved and d.weights["a"] == 0.1

    def test_rejects_nan_weights(self, engine):
        w = _w(a=0.1, b=0.1)
        w["b"] = float("nan")
        d = engine.approve(w, equity=100_000, high_water_mark=100_000)
        assert not d.approved and "finite_nonneg" in d.checks
        assert (d.weights == 0).all()  # rejected proposal is zeroed

    def test_rejects_negative_and_inf(self, engine):
        for bad in (-0.1, float("inf")):
            w = _w(a=0.1)
            w["a"] = bad
            d = engine.approve(w, equity=100_000, high_water_mark=100_000)
            assert not d.approved

    def test_max_positions(self, engine):
        w = _w(**{f"s{i}": 0.05 for i in range(9)})  # cap is 8
        d = engine.approve(w, equity=100_000, high_water_mark=100_000)
        assert not d.approved and "max_positions" in d.checks

    def test_position_weight_cap(self, engine):
        d = engine.approve(_w(a=0.5), equity=100_000, high_water_mark=100_000)  # cap 0.2
        assert not d.approved and "max_position_weight" in d.checks

    def test_gross_exposure_cap(self):
        w = _w(**{f"s{i}": 0.19 for i in range(5)})  # 0.95 > 0.9 cap
        d = RiskEngine(_settings(gross=0.9)).approve(w, equity=100_000, high_water_mark=100_000)
        assert not d.approved and "max_gross" in d.checks

    def test_drawdown_triggers_kill_switch(self, tmp_path):
        ks = KillSwitch(path=tmp_path / "kill.json")
        eng = RiskEngine(_settings(), ks)
        d = eng.approve(_w(a=0.1), equity=85_000, high_water_mark=100_000)  # -15% < -10%
        assert not d.approved
        assert ks.is_triggered
        # subsequent approvals blocked even at healthy equity
        d2 = eng.approve(_w(a=0.1), equity=100_000, high_water_mark=100_000)
        assert not d2.approved and "kill_switch" in d2.checks

    def test_kill_switch_blocks_everything(self, engine):
        engine.kill_switch.trigger("manual")
        d = engine.approve(_w(a=0.05), equity=100_000, high_water_mark=100_000)
        assert not d.approved and "kill_switch" in d.checks


def _settings(gross=1.0):
    from trbot.config import Settings

    return Settings.model_validate(
        {"backtest": {"max_positions": 8, "max_position_weight": 0.2, "max_gross_exposure": gross}}
    )


class TestPortfolio:
    def test_buy_then_sell_cash_math(self):
        pf = Portfolio(cash=10_000)
        pf.apply_fill(Fill(pd.Timestamp("2024-01-02"), "AAPL", "buy", qty=10, price=100, commission=1.0, notional=1000))
        assert pf.cash == pytest.approx(9_000 - 1.0)
        assert pf.positions["AAPL"].qty == 10
        assert pf.positions["AAPL"].avg_cost == pytest.approx((1000 + 1) / 10)
        pf.apply_fill(
            Fill(pd.Timestamp("2024-01-03"), "AAPL", "sell", qty=10, price=110, commission=1.1, notional=1100)
        )
        assert pf.cash == pytest.approx(9_000 - 1.0 + 1100 - 1.1)
        assert pf.realized_pnl == pytest.approx((1100 - 1.1) - (1000 + 1.0))
        assert not pf.positions["AAPL"].is_open

    def test_market_value_and_weights(self):
        pf = Portfolio(cash=5_000)
        pf.apply_fill(Fill(pd.Timestamp("2024-01-02"), "AAPL", "buy", qty=10, price=100, commission=0, notional=1000))
        pf.apply_fill(Fill(pd.Timestamp("2024-01-02"), "MSFT", "buy", qty=5, price=200, commission=0, notional=1000))
        prices = pd.Series({"AAPL": 120.0, "MSFT": 180.0})
        assert pf.market_value(prices) == pytest.approx(1200 + 900)
        assert pf.cash == pytest.approx(3_000)  # 5,000 initial minus 2 buys of 1,000
        assert pf.equity(prices) == pytest.approx(3_000 + 2_100)
        w = pf.current_weights(prices, pf.equity(prices))
        assert w["AAPL"] == pytest.approx(1200 / 5_100)

    def test_bad_fill_rejected(self):
        with pytest.raises(ValueError):
            Fill(pd.Timestamp("2024-01-02"), "AAPL", "sideways", qty=1, price=1, commission=0, notional=1)


class TestSimBroker:
    def test_orders_skip_noise_and_chunk(self, sim_settings):
        broker = SimBroker(sim_settings)
        equity = 100_000
        current = _w(a=0.10, b=0.05)
        target = _w(a=0.13, b=0.0, c=0.30)  # a: +3% ok; b: -5% sell; c: +30% > 10% cap
        orders = broker.orders_from_weights(current, target, equity)
        by_sym = {s: (side, n) for s, side, n in orders}
        assert by_sym["a"][0] == "buy" and by_sym["a"][1] == pytest.approx(3_000)
        assert by_sym["b"][0] == "sell" and by_sym["b"][1] == pytest.approx(5_000)
        assert by_sym["c"][1] == pytest.approx(10_000)  # chunked to order cap (10%)

    def test_min_notional_noise_skipped(self, sim_settings):
        broker = SimBroker(sim_settings)
        orders = broker.orders_from_weights(_w(a=0.100), _w(a=0.1005), 100_000)
        assert orders == []

    def test_slippage_direction(self, sim_settings):
        broker = SimBroker(sim_settings)
        pf = Portfolio(cash=100_000)
        prices = pd.Series({"AAPL": 100.0})
        fills = broker.execute([("AAPL", "buy", 10_000)], prices, pd.Timestamp("2024-01-02"), pf)
        assert fills[0].price == pytest.approx(100.0 * 1.0002)  # buy pays up
        fills2 = broker.execute([("AAPL", "sell", 10_000)], prices, pd.Timestamp("2024-01-02"), pf)
        assert fills2[0].price == pytest.approx(100.0 * (1 - 0.0002))  # sell receives less

    def test_missing_price_lapses_order(self, sim_settings):
        broker = SimBroker(sim_settings)
        pf = Portfolio(cash=100_000)
        fills = broker.execute([("ZZZ", "buy", 10_000)], pd.Series({"AAPL": 100.0}), pd.Timestamp("2024-01-02"), pf)
        assert fills == []

    def test_commission_applied(self, sim_settings):
        broker = SimBroker(sim_settings)
        pf = Portfolio(cash=100_000)
        fills = broker.execute([("AAPL", "buy", 10_000)], pd.Series({"AAPL": 100.0}), pd.Timestamp("2024-01-02"), pf)
        assert fills[0].commission == pytest.approx(10_000 * 1e-4)


class TestScaleMode:
    """on_violation=scale: research convenience — cap-and-renormalize with stamp."""

    def _engine(self, gross=1.0):
        from trbot.config import Settings
        from trbot.risk import RiskEngine as RE

        s = Settings.model_validate(
            {
                "backtest": {"max_positions": 8, "max_position_weight": 0.2, "max_gross_exposure": gross},
                "risk": {"on_violation": "scale"},
            }
        )
        return RE(s)

    def test_position_cap_scales_not_rejects(self):
        d = self._engine().approve(_w(a=0.5, b=0.1), equity=100_000, high_water_mark=100_000)
        assert d.approved and "scaled" in d.checks["ok"]
        assert d.weights["a"] == pytest.approx(0.2)  # capped at max_position_weight
        assert d.weights["b"] == pytest.approx(0.1)
        assert d.weights.sum() <= 1.0 + 1e-9

    def test_max_positions_trimmed(self):
        w = _w(**{f"s{i}": 0.1 for i in range(9)})
        d = self._engine().approve(w, equity=100_000, high_water_mark=100_000)
        assert d.approved
        assert (d.weights > 1e-9).sum() == 8  # trimmed to max_positions
        assert d.weights["s0"] == 0.1

    def test_gross_scaled(self):
        w = _w(**{f"s{i}": 0.19 for i in range(5)})
        d = self._engine(gross=0.9).approve(w, equity=100_000, high_water_mark=100_000)
        assert d.approved and d.weights.sum() == pytest.approx(0.9, abs=1e-9)

    def test_still_rejects_garbage(self):
        w = _w(a=0.1)
        w["b"] = float("nan")
        d = self._engine().approve(w, equity=100_000, high_water_mark=100_000)
        assert not d.approved  # scale never launders NaN

    def test_kill_switch_still_blocks(self):
        eng = self._engine()
        eng.kill_switch.trigger("x")
        d = eng.approve(_w(a=0.5), equity=100_000, high_water_mark=100_000)
        assert not d.approved
