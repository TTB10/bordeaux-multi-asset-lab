"""Unit tests for the risk module."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from bml.risk import (
    HistoricalRiskCalculator,
    RiskMetrics,
    portfolio_levels,
    portfolio_returns,
)


def _trending_series(
    daily_drift: float,
    daily_noise_std: float = 0.001,
    n_days: int = 750,
    seed: int = 0,
) -> pd.Series:
    """Build a deterministic price series for stable test assertions."""
    rng = np.random.default_rng(seed=seed)
    daily_returns = np.full(n_days, daily_drift) + rng.normal(0.0, daily_noise_std, size=n_days)
    levels = 100.0 * np.exp(np.cumsum(daily_returns))
    dates = pd.date_range(end="2026-05-01", periods=n_days, freq="B")
    return pd.Series(levels, index=dates, name="X")


class TestRiskMetricsModel:
    def test_summary_includes_all_fields(self) -> None:
        m = RiskMetrics(
            as_of=date(2026, 5, 1),
            horizon_days=750,
            annual_return=0.12,
            annual_volatility=0.10,
            sharpe_ratio=1.2,
            max_drawdown=-0.15,
            var_95=-0.018,
            cvar_95=-0.025,
            beta=0.85,
        )
        s = m.summary()
        assert "12.00%" in s
        assert "sharpe=+1.20" in s
        assert "beta=+0.85" in s

    def test_max_drawdown_must_be_non_positive(self) -> None:
        with pytest.raises(ValidationError):
            RiskMetrics(
                as_of=date(2026, 5, 1),
                horizon_days=100,
                annual_return=0.05,
                annual_volatility=0.10,
                sharpe_ratio=0.5,
                max_drawdown=0.05,  # invalid: positive
                var_95=-0.02,
                cvar_95=-0.03,
            )

    def test_beta_can_be_none(self) -> None:
        m = RiskMetrics(
            as_of=date(2026, 5, 1),
            horizon_days=100,
            annual_return=0.05,
            annual_volatility=0.10,
            sharpe_ratio=0.5,
            max_drawdown=-0.1,
            var_95=-0.02,
            cvar_95=-0.03,
        )
        assert m.beta is None
        assert "beta=n/a" in m.summary()


class TestHistoricalRiskCalculator:
    def test_strong_uptrend_has_positive_return_and_low_drawdown(self) -> None:
        calc = HistoricalRiskCalculator()
        prices = _trending_series(daily_drift=0.0008, daily_noise_std=0.001, seed=1)
        m = calc.compute(prices, as_of=date(2026, 5, 1))

        assert m.annual_return > 0.15  # ~20% annual
        assert m.annual_volatility > 0.0
        assert m.sharpe_ratio > 1.0  # strong trend, low noise -> high Sharpe
        assert -0.05 < m.max_drawdown <= 0.0  # very small DD
        assert m.var_95 < 0.0
        assert m.cvar_95 <= m.var_95  # CVaR is always <= VaR

    def test_downtrend_produces_negative_metrics(self) -> None:
        calc = HistoricalRiskCalculator()
        prices = _trending_series(daily_drift=-0.0005, daily_noise_std=0.001, seed=2)
        m = calc.compute(prices, as_of=date(2026, 5, 1))

        assert m.annual_return < 0.0
        assert m.max_drawdown < 0.0  # significant DD on downtrend
        assert m.sharpe_ratio < 0.0

    def test_short_history_returns_neutral_metrics(self) -> None:
        calc = HistoricalRiskCalculator()
        prices = _trending_series(daily_drift=0.001, n_days=10)  # below MIN_OBSERVATIONS
        m = calc.compute(prices, as_of=date(2026, 5, 1))

        assert m.annual_return == 0.0
        assert m.annual_volatility == 0.0
        assert m.sharpe_ratio == 0.0
        assert m.max_drawdown == 0.0

    def test_beta_is_one_when_asset_equals_benchmark(self) -> None:
        calc = HistoricalRiskCalculator()
        prices = _trending_series(daily_drift=0.0005, daily_noise_std=0.005, seed=3)
        m = calc.compute(prices, benchmark_prices=prices, as_of=date(2026, 5, 1))
        assert m.beta == pytest.approx(1.0, abs=1e-6)

    def test_beta_is_higher_for_amplified_asset(self) -> None:
        """If asset returns = 2 * benchmark returns, beta should be ~2."""
        calc = HistoricalRiskCalculator()
        rng = np.random.default_rng(seed=42)
        n = 500
        bench_daily_returns = rng.normal(0.0003, 0.01, size=n)
        bench_levels = 100.0 * np.exp(np.cumsum(bench_daily_returns))
        # Asset has twice the daily returns
        asset_daily_returns = 2.0 * bench_daily_returns
        asset_levels = 100.0 * np.exp(np.cumsum(asset_daily_returns))
        dates = pd.date_range(end="2026-05-01", periods=n, freq="B")

        bench = pd.Series(bench_levels, index=dates)
        asset = pd.Series(asset_levels, index=dates)

        m = calc.compute(asset, benchmark_prices=bench, as_of=date(2026, 5, 1))
        assert m.beta == pytest.approx(2.0, abs=0.05)

    def test_beta_is_none_when_no_benchmark(self) -> None:
        calc = HistoricalRiskCalculator()
        prices = _trending_series(daily_drift=0.0005, seed=4)
        m = calc.compute(prices, as_of=date(2026, 5, 1))
        assert m.beta is None

    def test_invalid_alpha_raises(self) -> None:
        with pytest.raises(ValueError, match="var_alpha"):
            HistoricalRiskCalculator(var_alpha=0.6)

    def test_constant_prices_yield_zero_vol(self) -> None:
        calc = HistoricalRiskCalculator()
        flat = pd.Series(
            [100.0] * 100,
            index=pd.date_range(end="2026-05-01", periods=100, freq="B"),
        )
        m = calc.compute(flat, as_of=date(2026, 5, 1))
        assert m.annual_volatility == pytest.approx(0.0)
        assert m.sharpe_ratio == 0.0


class TestPortfolioReturns:
    def _two_asset_prices(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "A": _trending_series(0.001, daily_noise_std=0.005, seed=10),
                "B": _trending_series(-0.0005, daily_noise_std=0.005, seed=11),
            }
        )

    def test_equal_weight_is_average(self) -> None:
        prices = self._two_asset_prices()
        returns = portfolio_returns(prices, {"A": 0.5, "B": 0.5})
        a_ret = prices["A"].pct_change().dropna()
        b_ret = prices["B"].pct_change().dropna()
        expected = (a_ret + b_ret) / 2.0
        # Same length and very close values
        aligned = pd.DataFrame({"got": returns, "expected": expected}).dropna()
        assert (aligned["got"] - aligned["expected"]).abs().max() < 1e-9

    def test_full_weight_one_asset(self) -> None:
        prices = self._two_asset_prices()
        returns = portfolio_returns(prices, {"A": 1.0, "B": 0.0})
        a_ret = prices["A"].pct_change().dropna()
        aligned = pd.DataFrame({"got": returns, "a": a_ret}).dropna()
        assert (aligned["got"] - aligned["a"]).abs().max() < 1e-9

    def test_renormalises_unscaled_weights(self) -> None:
        prices = self._two_asset_prices()
        returns_norm = portfolio_returns(prices, {"A": 0.5, "B": 0.5})
        returns_scaled = portfolio_returns(prices, {"A": 50.0, "B": 50.0})
        # Should be identical: weights renormalise to sum=1
        aligned = pd.DataFrame({"a": returns_norm, "b": returns_scaled}).dropna()
        assert (aligned["a"] - aligned["b"]).abs().max() < 1e-9

    def test_missing_ticker_silently_skipped(self) -> None:
        prices = self._two_asset_prices()
        returns = portfolio_returns(prices, {"A": 0.5, "B": 0.3, "MISSING": 0.2})
        # Should still produce results, only A and B contribute
        assert len(returns) > 0

    def test_empty_weights_returns_empty(self) -> None:
        prices = self._two_asset_prices()
        assert portfolio_returns(prices, {}).empty

    def test_portfolio_levels_round_trip(self) -> None:
        prices = self._two_asset_prices()
        returns = portfolio_returns(prices, {"A": 0.6, "B": 0.4})
        levels = portfolio_levels(returns, base=100.0)
        assert levels.iloc[0] > 0
        # Levels should be monotonically related to cumulative returns
        cum = (1.0 + returns).cumprod() * 100.0
        diff = (levels - cum).abs().max()
        assert diff < 1e-9
