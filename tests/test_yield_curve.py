"""Unit tests for YieldCurveIndicator using a mocked MacroDataProvider."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime.enums import Direction, MacroDimension
from bml.regime.indicators import YieldCurveIndicator


def _build_provider(values: pd.Series) -> MacroDataProvider:
    """Return a mocked MacroDataProvider that returns `values` for any series."""
    provider = MagicMock(spec=MacroDataProvider)
    provider.fetch_series.return_value = values
    return provider


def _series_around(mean: float, std: float, n: int = 1500, last: float | None = None) -> pd.Series:
    """Generate a synthetic daily series with given mean and std.

    If `last` is provided, the final value is overridden — useful for
    testing point-in-time decision logic.
    """
    rng = np.random.default_rng(seed=42)
    dates = pd.date_range(end="2026-05-01", periods=n, freq="B")
    values = rng.normal(mean, std, size=n)
    if last is not None:
        values[-1] = last
    return pd.Series(values, index=dates, name="T10Y3M")


class TestYieldCurveBasics:
    def test_name_and_dimension(self) -> None:
        indicator = YieldCurveIndicator(_build_provider(_series_around(1.0, 0.5)))
        assert indicator.name == "yield_curve_10y3m"
        assert indicator.dimension == MacroDimension.GROWTH

    def test_empty_history_raises(self) -> None:
        empty = pd.Series([], dtype=float, name="T10Y3M", index=pd.DatetimeIndex([]))
        indicator = YieldCurveIndicator(_build_provider(empty))
        with pytest.raises(ValueError, match="No data returned"):
            indicator.read(as_of=date(2026, 5, 1))


class TestInversionOverride:
    """When the curve is inverted, return DOWN with high confidence regardless of z-score."""

    def test_strong_inversion_returns_down(self) -> None:
        series = _series_around(0.5, 0.3, last=-0.8)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.DOWN
        assert reading.confidence == 0.9
        assert reading.z_score is None  # inversion path skips z-score
        assert reading.value == pytest.approx(-0.8)

    def test_mild_inversion_below_threshold_returns_down(self) -> None:
        series = _series_around(0.5, 0.3, last=-0.30)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.DOWN

    def test_just_above_threshold_does_not_force_down(self) -> None:
        # Slightly above -0.25, should fall through to z-score logic
        series = _series_around(0.5, 0.3, last=-0.20)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        # Value is below the historical mean of 0.5, z should be negative
        assert reading.z_score is not None
        assert reading.z_score < 0


class TestZScoreLogic:
    """When the curve is not inverted, classification follows a 5y z-score."""

    def test_steep_curve_returns_up(self) -> None:
        # Last value 2 sigma above mean -> strongly UP
        series = _series_around(1.0, 0.4, last=1.8)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.UP
        assert reading.z_score is not None
        assert reading.z_score > 0.5
        assert reading.confidence > 0.5

    def test_flat_curve_around_mean_is_neutral(self) -> None:
        series = _series_around(1.0, 0.4, last=1.05)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.NEUTRAL
        assert reading.z_score is not None
        assert abs(reading.z_score) <= 0.5

    def test_flattening_curve_returns_down(self) -> None:
        # Last value 1.5 sigma below mean -> DOWN (slowdown signal)
        series = _series_around(1.5, 0.4, last=0.5)
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.DOWN
        assert reading.z_score is not None
        assert reading.z_score < -0.5


class TestEdgeCases:
    def test_short_window_returns_neutral_with_low_confidence(self) -> None:
        # Only 30 days of data, less than the 60-day minimum
        rng = np.random.default_rng(seed=7)
        dates = pd.date_range(end="2026-05-01", periods=30, freq="B")
        values = rng.normal(0.5, 0.2, size=30)
        series = pd.Series(values, index=dates, name="T10Y3M")
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.NEUTRAL
        assert reading.confidence == 0.3
        assert reading.z_score is None

    def test_zero_std_returns_neutral(self) -> None:
        # All values identical -> std=0, z forced to 0
        dates = pd.date_range(end="2026-05-01", periods=200, freq="B")
        series = pd.Series([1.0] * 200, index=dates, name="T10Y3M")
        indicator = YieldCurveIndicator(_build_provider(series))
        reading = indicator.read(as_of=date(2026, 5, 1))
        assert reading.direction == Direction.NEUTRAL
        assert reading.z_score == 0.0
