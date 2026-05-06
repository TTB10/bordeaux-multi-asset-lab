"""Pydantic models carrying the regime detection pipeline output."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from bml.regime.enums import Direction, MacroDimension, Regime


class IndicatorReading(BaseModel):
    """Output of a single macro indicator at a given as-of date.

    Attributes:
        indicator_name: Short identifier (e.g. 'yield_curve_10y3m').
        dimension: GROWTH or INFLATION.
        as_of: Reference date for the reading.
        value: Raw value of the underlying time series.
        z_score: Standardized value vs historical distribution (None if N/A).
        direction: UP, DOWN or NEUTRAL.
        confidence: How strong the signal is, in [0, 1].
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    indicator_name: str = Field(min_length=1)
    dimension: MacroDimension
    as_of: date
    value: float
    z_score: float | None = None
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0)


class DimensionalSignal(BaseModel):
    """Aggregated signal for one macro dimension.

    Combines multiple IndicatorReading instances into a single direction
    plus a continuous score in [-1, +1] (negative = DOWN, positive = UP).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: MacroDimension
    as_of: date
    direction: Direction
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_readings: list[IndicatorReading]


class RegimeSignal(BaseModel):
    """Final regime detection output at a given as-of date."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    regime: Regime
    growth_signal: DimensionalSignal
    inflation_signal: DimensionalSignal
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def is_decisive(self) -> bool:
        """True when neither dimension is NEUTRAL."""
        return self.regime != Regime.UNCERTAIN
