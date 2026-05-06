"""Unit tests for regime domain models and enums."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from bml.regime import (
    DimensionalSignal,
    Direction,
    IndicatorReading,
    MacroDimension,
    Regime,
    RegimeSignal,
)


class TestRegimeFromDirections:
    """Verify the 2x2 Bridgewater mapping."""

    @pytest.mark.parametrize(
        ("growth", "inflation", "expected"),
        [
            (Direction.UP, Direction.DOWN, Regime.GOLDILOCKS),
            (Direction.UP, Direction.UP, Regime.REFLATION),
            (Direction.DOWN, Direction.DOWN, Regime.DISINFLATION_RECESSION),
            (Direction.DOWN, Direction.UP, Regime.STAGFLATION),
        ],
    )
    def test_pure_quadrants(
        self,
        growth: Direction,
        inflation: Direction,
        expected: Regime,
    ) -> None:
        assert Regime.from_directions(growth, inflation) == expected

    @pytest.mark.parametrize(
        ("growth", "inflation"),
        [
            (Direction.NEUTRAL, Direction.UP),
            (Direction.UP, Direction.NEUTRAL),
            (Direction.NEUTRAL, Direction.NEUTRAL),
        ],
    )
    def test_neutral_resolves_to_uncertain(
        self,
        growth: Direction,
        inflation: Direction,
    ) -> None:
        assert Regime.from_directions(growth, inflation) == Regime.UNCERTAIN


class TestIndicatorReading:
    def _build(self, **overrides: object) -> IndicatorReading:
        defaults: dict[str, object] = {
            "indicator_name": "yield_curve_10y3m",
            "dimension": MacroDimension.GROWTH,
            "as_of": date(2026, 5, 1),
            "value": -0.45,
            "z_score": -1.8,
            "direction": Direction.DOWN,
            "confidence": 0.9,
        }
        defaults.update(overrides)
        return IndicatorReading(**defaults)  # type: ignore[arg-type]

    def test_valid_reading(self) -> None:
        r = self._build()
        assert r.indicator_name == "yield_curve_10y3m"
        assert r.direction == Direction.DOWN

    def test_reading_is_frozen(self) -> None:
        r = self._build()
        with pytest.raises(ValidationError):
            r.confidence = 0.5

    def test_confidence_must_be_in_unit_interval(self) -> None:
        with pytest.raises(ValidationError):
            self._build(confidence=1.5)
        with pytest.raises(ValidationError):
            self._build(confidence=-0.1)

    def test_indicator_name_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            self._build(indicator_name="")


class TestDimensionalSignal:
    def _build_reading(self) -> IndicatorReading:
        return IndicatorReading(
            indicator_name="ind1",
            dimension=MacroDimension.GROWTH,
            as_of=date(2026, 5, 1),
            value=1.0,
            direction=Direction.UP,
            confidence=0.8,
        )

    def test_valid_signal(self) -> None:
        s = DimensionalSignal(
            dimension=MacroDimension.GROWTH,
            as_of=date(2026, 5, 1),
            direction=Direction.UP,
            score=0.7,
            confidence=0.85,
            contributing_readings=[self._build_reading()],
        )
        assert s.direction == Direction.UP
        assert len(s.contributing_readings) == 1

    def test_score_must_be_in_range(self) -> None:
        with pytest.raises(ValidationError):
            DimensionalSignal(
                dimension=MacroDimension.GROWTH,
                as_of=date(2026, 5, 1),
                direction=Direction.UP,
                score=1.5,
                confidence=0.5,
                contributing_readings=[],
            )


class TestRegimeSignal:
    def _build_signal(self, growth_dir: Direction, infl_dir: Direction) -> RegimeSignal:
        ref = date(2026, 5, 1)
        growth = DimensionalSignal(
            dimension=MacroDimension.GROWTH,
            as_of=ref,
            direction=growth_dir,
            score=0.5 if growth_dir == Direction.UP else -0.5,
            confidence=0.8,
            contributing_readings=[],
        )
        inflation = DimensionalSignal(
            dimension=MacroDimension.INFLATION,
            as_of=ref,
            direction=infl_dir,
            score=0.5 if infl_dir == Direction.UP else -0.5,
            confidence=0.8,
            contributing_readings=[],
        )
        return RegimeSignal(
            as_of=ref,
            regime=Regime.from_directions(growth_dir, infl_dir),
            growth_signal=growth,
            inflation_signal=inflation,
            confidence=0.8,
        )

    def test_decisive_regime(self) -> None:
        sig = self._build_signal(Direction.UP, Direction.DOWN)
        assert sig.regime == Regime.GOLDILOCKS
        assert sig.is_decisive is True

    def test_uncertain_regime(self) -> None:
        sig = self._build_signal(Direction.NEUTRAL, Direction.DOWN)
        assert sig.regime == Regime.UNCERTAIN
        assert sig.is_decisive is False
