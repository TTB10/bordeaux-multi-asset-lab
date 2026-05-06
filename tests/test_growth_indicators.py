"""Unit tests for IndustrialProductionIndicator and JoblessClaimsIndicator."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime.enums import Direction, MacroDimension
from bml.regime.indicators import (
    IndustrialProductionIndicator,
    JoblessClaimsIndicator,
)


def _build_provider(values: pd.Series) -> MacroDataProvider:
    provider = MagicMock(spec=MacroDataProvider)
    provider.fetch_series.return_value = values
    return provider


class TestIndustrialProduction:
    def _series(self, last_yoy_pct: float, n_months: int = 240) -> pd.Series:
        """Build a synthetic INDPRO series whose final YoY change is `last_yoy_pct` percent."""
        rng = np.random.default_rng(seed=11)
        dates = pd.date_range(end="2026-04-01", periods=n_months, freq="MS")
        # Random walk around a trend; we will overwrite the final value.
        log_levels = np.cumsum(rng.normal(0.002, 0.005, size=n_months))
        levels = np.exp(log_levels) * 100.0
        # Force the final point to imply the requested YoY change.
        target = levels[-13] * (1 + last_yoy_pct / 100.0)
        levels[-1] = target
        return pd.Series(levels, index=dates, name="INDPRO")

    def test_name_and_dimension(self) -> None:
        ind = IndustrialProductionIndicator(_build_provider(self._series(0.0)))
        assert ind.name == "industrial_production_yoy"
        assert ind.dimension == MacroDimension.GROWTH

    def test_strong_positive_yoy_returns_up(self) -> None:
        ind = IndustrialProductionIndicator(_build_provider(self._series(8.0)))
        reading = ind.read(as_of=date(2026, 4, 1))
        assert reading.direction == Direction.UP
        assert reading.z_score is not None
        assert reading.z_score > 0.5

    def test_strong_negative_yoy_returns_down(self) -> None:
        ind = IndustrialProductionIndicator(_build_provider(self._series(-6.0)))
        reading = ind.read(as_of=date(2026, 4, 1))
        assert reading.direction == Direction.DOWN
        assert reading.z_score is not None
        assert reading.z_score < -0.5

    def test_empty_history_raises(self) -> None:
        empty = pd.Series([], dtype=float, index=pd.DatetimeIndex([]), name="INDPRO")
        ind = IndustrialProductionIndicator(_build_provider(empty))
        with pytest.raises(ValueError, match="No data returned"):
            ind.read(as_of=date(2026, 4, 1))


class TestJoblessClaims:
    def _series(self, mean_level: float = 230_000.0, last_value: float | None = None) -> pd.Series:
        rng = np.random.default_rng(seed=23)
        n_weeks = 1500  # ~30 years of weekly data
        dates = pd.date_range(end="2026-05-02", periods=n_weeks, freq="W-SAT")
        values = rng.normal(mean_level, mean_level * 0.05, size=n_weeks)
        if last_value is not None:
            # Override the last 4 weeks so the 4-week MA reflects the intended signal.
            values[-4:] = last_value
        return pd.Series(values, index=dates, name="ICSA")

    def test_name_and_dimension(self) -> None:
        ind = JoblessClaimsIndicator(_build_provider(self._series()))
        assert ind.name == "initial_jobless_claims_4wk_ma"
        assert ind.dimension == MacroDimension.GROWTH

    def test_high_claims_returns_down(self) -> None:
        # Last week well above the 230k mean -> growth DOWN (sign inverted)
        ind = JoblessClaimsIndicator(_build_provider(self._series(last_value=320_000.0)))
        reading = ind.read(as_of=date(2026, 5, 2))
        assert reading.direction == Direction.DOWN

    def test_low_claims_returns_up(self) -> None:
        # Last week well below the mean -> growth UP
        ind = JoblessClaimsIndicator(_build_provider(self._series(last_value=180_000.0)))
        reading = ind.read(as_of=date(2026, 5, 2))
        assert reading.direction == Direction.UP

    def test_claims_around_mean_is_neutral(self) -> None:
        ind = JoblessClaimsIndicator(_build_provider(self._series(last_value=232_000.0)))
        reading = ind.read(as_of=date(2026, 5, 2))
        assert reading.direction == Direction.NEUTRAL

    def test_sign_inversion_z_score_unchanged(self) -> None:
        """The raw z_score returned must NOT be inverted; only the direction is."""
        ind = JoblessClaimsIndicator(_build_provider(self._series(last_value=320_000.0)))
        reading = ind.read(as_of=date(2026, 5, 2))
        # Last value is above mean -> raw z is positive
        assert reading.z_score is not None
        assert reading.z_score > 0
        # But direction is DOWN because high claims = bad for growth
        assert reading.direction == Direction.DOWN
