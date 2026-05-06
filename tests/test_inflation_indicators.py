"""Unit tests for inflation indicators."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime.enums import Direction, MacroDimension
from bml.regime.indicators import (
    CoreCPIIndicator,
    InflationBreakevenIndicator,
    OilMomentumIndicator,
)


def _build_provider(values: pd.Series) -> MacroDataProvider:
    provider = MagicMock(spec=MacroDataProvider)
    provider.fetch_series.return_value = values
    return provider


class TestInflationBreakeven:
    def _series(self, mean: float = 2.3, std: float = 0.3, last: float | None = None) -> pd.Series:
        rng = np.random.default_rng(seed=31)
        n = 1500  # daily data for ~6 years
        dates = pd.date_range(end="2026-05-01", periods=n, freq="B")
        values = rng.normal(mean, std, size=n)
        if last is not None:
            values[-1] = last
        return pd.Series(values, index=dates, name="T5YIFR")

    def test_name_and_dimension(self) -> None:
        ind = InflationBreakevenIndicator(_build_provider(self._series()))
        assert ind.name == "inflation_breakeven_5y5y"
        assert ind.dimension == MacroDimension.INFLATION

    def test_high_breakeven_returns_up(self) -> None:
        ind = InflationBreakevenIndicator(_build_provider(self._series(last=3.5)))
        reading = ind.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.UP
        assert reading.z_score is not None
        assert reading.z_score > 0.5

    def test_low_breakeven_returns_down(self) -> None:
        ind = InflationBreakevenIndicator(_build_provider(self._series(last=1.5)))
        reading = ind.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.DOWN
        assert reading.z_score is not None
        assert reading.z_score < -0.5

    def test_breakeven_around_mean_is_neutral(self) -> None:
        ind = InflationBreakevenIndicator(_build_provider(self._series(last=2.32)))
        reading = ind.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.NEUTRAL

    def test_empty_history_raises(self) -> None:
        empty = pd.Series([], dtype=float, index=pd.DatetimeIndex([]), name="T5YIFR")
        ind = InflationBreakevenIndicator(_build_provider(empty))
        with pytest.raises(ValueError, match="No data returned"):
            ind.read(as_of=date(2026, 5, 1))


class TestCoreCPI:
    def _series(self, last_yoy_pct: float, n_months: int = 240) -> pd.Series:
        rng = np.random.default_rng(seed=37)
        dates = pd.date_range(end="2026-04-01", periods=n_months, freq="MS")
        log_levels = np.cumsum(rng.normal(0.002, 0.001, size=n_months))
        levels = np.exp(log_levels) * 250.0
        # Override last 12 months consistently so the YoY at end equals last_yoy_pct
        levels[-1] = levels[-13] * (1 + last_yoy_pct / 100.0)
        return pd.Series(levels, index=dates, name="CPILFESL")

    def test_name_and_dimension(self) -> None:
        ind = CoreCPIIndicator(_build_provider(self._series(2.5)))
        assert ind.name == "core_cpi_yoy"
        assert ind.dimension == MacroDimension.INFLATION

    def test_high_yoy_returns_up(self) -> None:
        ind = CoreCPIIndicator(_build_provider(self._series(5.0)))
        reading = ind.read(as_of=date(2026, 4, 1))
        assert reading.direction == Direction.UP
        assert reading.z_score is not None
        assert reading.z_score > 0.5

    def test_low_yoy_returns_down(self) -> None:
        ind = CoreCPIIndicator(_build_provider(self._series(0.5)))
        reading = ind.read(as_of=date(2026, 4, 1))
        assert reading.direction == Direction.DOWN
        assert reading.z_score is not None
        assert reading.z_score < -0.5


class TestOilMomentum:
    def _series(self, last_6m_pct: float = 0.0, n_days: int = 1500) -> pd.Series:
        """Build a daily Brent series whose 6m momentum at end equals last_6m_pct."""
        rng = np.random.default_rng(seed=41)
        dates = pd.date_range(end="2026-05-01", periods=n_days, freq="B")
        log_returns = rng.normal(0.0, 0.015, size=n_days)
        levels = 70.0 * np.exp(np.cumsum(log_returns))
        # Force the last point so that 126-day momentum = last_6m_pct percent
        levels[-1] = levels[-127] * (1 + last_6m_pct / 100.0)
        return pd.Series(levels, index=dates, name="DCOILWTICO")

    def test_name_and_dimension(self) -> None:
        ind = OilMomentumIndicator(_build_provider(self._series()))
        assert ind.name == "wti_oil_6m_momentum"
        assert ind.dimension == MacroDimension.INFLATION

    def test_strong_positive_momentum_returns_up(self) -> None:
        ind = OilMomentumIndicator(_build_provider(self._series(last_6m_pct=40.0)))
        reading = ind.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.UP

    def test_strong_negative_momentum_returns_down(self) -> None:
        ind = OilMomentumIndicator(_build_provider(self._series(last_6m_pct=-35.0)))
        reading = ind.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.DOWN
