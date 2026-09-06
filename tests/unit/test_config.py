"""Config guard tests — the paper-only safety contract."""

import pytest

from trbot.config import Mode, Settings, load_settings


class TestModeGuard:
    def test_default_is_simulation(self):
        assert Settings().mode is Mode.SIMULATION

    def test_paper_accepted(self):
        assert Settings.model_validate({"mode": "paper"}).mode is Mode.PAPER

    def test_case_insensitive(self):
        assert Settings.model_validate({"mode": "Simulation"}).mode is Mode.SIMULATION

    @pytest.mark.parametrize("bad", ["live", "LIVE", "real", "production", "prod", "broker", ""])
    def test_forbidden_modes_rejected(self, bad):
        with pytest.raises(ValueError, match="refusing forbidden|unknown mode"):
            Settings.model_validate({"mode": bad})

    def test_none_mode_rejected(self):
        with pytest.raises(ValueError, match="must not be empty"):
            Settings.model_validate({"mode": None})


class TestOrdersDoubleGate:
    def test_orders_disabled_by_default(self):
        s = Settings()
        assert s.orders.enabled is False
        assert s.orders_actually_enabled is False

    def test_orders_require_paper_mode(self):
        with pytest.raises(ValueError, match="requires mode=PAPER"):
            Settings.model_validate({"orders": {"enabled": True}})

    def test_config_flag_alone_is_not_sufficient(self, monkeypatch):
        monkeypatch.delenv("TRBOT_ORDERS_ENABLED", raising=False)
        s = Settings.model_validate({"mode": "paper", "orders": {"enabled": True}})
        assert s.orders.enabled is True
        assert s.orders_actually_enabled is False

    def test_env_var_alone_is_not_sufficient(self, monkeypatch):
        monkeypatch.setenv("TRBOT_ORDERS_ENABLED", "true")
        s = Settings(mode=Mode.PAPER)
        assert s.orders.enabled is False
        assert s.orders_actually_enabled is False

    def test_both_gates_open(self, monkeypatch):
        monkeypatch.setenv("TRBOT_ORDERS_ENABLED", "true")
        s = Settings.model_validate({"mode": "paper", "orders": {"enabled": True}})
        assert s.orders_actually_enabled is True


class TestBrokerUrlAllowlist:
    def test_paper_urls_accepted(self):
        s = Settings(mode=Mode.PAPER)
        assert s.broker.base_url.startswith("https://paper-api.alpaca.markets")

    @pytest.mark.parametrize(
        "bad",
        [
            "https://live-api.alpaca.markets",
            "https://api.alpaca.markets",  # not in allowlist even if not obviously live
            "https://paper-api.alpaca.markets.evil.com",
        ],
    )
    def test_non_paper_urls_rejected(self, bad):
        with pytest.raises(ValueError, match="refusing non-paper|not in paper allowlist"):
            Settings.model_validate({"broker": {"base_url": bad}})


class TestLoadSettings:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_settings(tmp_path / "nope.yaml")

    def test_yaml_merge_and_validation(self, tmp_path):
        p = tmp_path / "s.yaml"
        p.write_text("mode: paper\nbacktest:\n  initial_capital: 50000\n")
        s = load_settings(p)
        assert s.mode is Mode.PAPER
        assert s.backtest.initial_capital == 50_000
        assert s.backtest.commission_bps == 1.0  # default preserved (deep merge)

    def test_overrides_dict(self, tmp_path):
        p = tmp_path / "s.yaml"
        p.write_text("backtest:\n  initial_capital: 50000\n")
        s = load_settings(p, overrides={"backtest": {"slippage_bps": 5.0}})
        assert s.backtest.initial_capital == 50_000
        assert s.backtest.slippage_bps == 5.0

    def test_non_mapping_yaml_rejected(self, tmp_path):
        p = tmp_path / "s.yaml"
        p.write_text("- just\n- a list\n")
        with pytest.raises(ValueError, match="must contain a mapping"):
            load_settings(p)
