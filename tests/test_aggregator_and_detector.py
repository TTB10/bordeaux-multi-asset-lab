"""Unit tests for WeightedVoteAggregator and RuleBasedRegimeDetector."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bml.regime import (
    Direction,
    IndicatorReading,
    MacroDimension,
    MacroIndicator,
    Regime,
    RuleBasedRegimeDetector,
    WeightedVoteAggregator,
)


def _reading(
    direction: Direction,
    confidence: float,
    dimension: MacroDimension = MacroDimension.GROWTH,
    name: str = "test_indicator",
    value: float = 1.0,
) -> IndicatorReading:
    return IndicatorReading(
        indicator_name=name,
        dimension=dimension,
        as_of=date(2026, 5, 1),
        value=value,
        direction=direction,
        confidence=confidence,
    )


class TestWeightedVoteAggregator:
    def test_unanimous_up_returns_up(self) -> None:
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.UP, 0.8, name="a"),
            _reading(Direction.UP, 0.7, name="b"),
            _reading(Direction.UP, 0.9, name="c"),
        ]
        sig = agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))
        assert sig.direction == Direction.UP
        assert sig.score == pytest.approx(1.0)
        # confidence = |score| * mean(individual confidences) = 1.0 * 0.8 = 0.8
        assert sig.confidence == pytest.approx(0.8)

    def test_unanimous_down_returns_down(self) -> None:
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.DOWN, 0.6, name="a"),
            _reading(Direction.DOWN, 0.5, name="b"),
        ]
        sig = agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))
        assert sig.direction == Direction.DOWN
        assert sig.score == pytest.approx(-1.0)

    def test_balanced_up_down_is_neutral(self) -> None:
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.UP, 0.7, name="a"),
            _reading(Direction.DOWN, 0.7, name="b"),
        ]
        sig = agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))
        assert sig.direction == Direction.NEUTRAL
        assert abs(sig.score) < 0.01

    def test_high_confidence_dominates_low(self) -> None:
        """An indicator with 0.95 confidence outweighs two at 0.4."""
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.UP, 0.95, name="a"),
            _reading(Direction.DOWN, 0.4, name="b"),
            _reading(Direction.DOWN, 0.4, name="c"),
        ]
        sig = agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))
        # weighted_sum = +0.95 - 0.4 - 0.4 = +0.15
        # total_weight = 0.95 + 0.4 + 0.4 = 1.75
        # score ~ 0.086 -> below threshold 0.3 -> NEUTRAL
        assert sig.direction == Direction.NEUTRAL

    def test_neutral_indicator_does_not_count_as_vote(self) -> None:
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.UP, 0.8, name="a"),
            _reading(Direction.NEUTRAL, 0.5, name="b"),
        ]
        sig = agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))
        # weighted_sum = +0.8, total = 0.8 + 0.5 = 1.3, score ~ 0.615 -> UP
        assert sig.direction == Direction.UP
        assert sig.score == pytest.approx(0.615, abs=0.01)

    def test_empty_readings_raises(self) -> None:
        agg = WeightedVoteAggregator()
        with pytest.raises(ValueError, match="empty readings"):
            agg.aggregate([], MacroDimension.GROWTH, date(2026, 5, 1))

    def test_mixed_dimensions_raises(self) -> None:
        agg = WeightedVoteAggregator()
        readings = [
            _reading(Direction.UP, 0.8, dimension=MacroDimension.GROWTH, name="a"),
            _reading(Direction.UP, 0.6, dimension=MacroDimension.INFLATION, name="b"),
        ]
        with pytest.raises(ValueError, match="not in dimension"):
            agg.aggregate(readings, MacroDimension.GROWTH, date(2026, 5, 1))

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="score_threshold"):
            WeightedVoteAggregator(score_threshold=1.5)


def _make_indicator(
    name: str,
    dimension: MacroDimension,
    direction: Direction,
    confidence: float,
) -> MacroIndicator:
    """Build a mocked MacroIndicator that returns a fixed reading."""
    indicator = MagicMock(spec=MacroIndicator)
    indicator.name = name
    indicator.dimension = dimension
    indicator.read.return_value = _reading(
        direction=direction,
        confidence=confidence,
        dimension=dimension,
        name=name,
    )
    indicator.fetch_history.return_value = pd.Series(dtype=float)
    return indicator


class TestRuleBasedRegimeDetector:
    def test_clear_goldilocks(self) -> None:
        detector = RuleBasedRegimeDetector(
            indicators=[
                _make_indicator("g1", MacroDimension.GROWTH, Direction.UP, 0.85),
                _make_indicator("g2", MacroDimension.GROWTH, Direction.UP, 0.75),
                _make_indicator("i1", MacroDimension.INFLATION, Direction.DOWN, 0.80),
                _make_indicator("i2", MacroDimension.INFLATION, Direction.DOWN, 0.70),
            ],
        )
        signal = detector.detect(as_of=date(2026, 5, 1))
        assert signal.regime == Regime.GOLDILOCKS
        assert signal.growth_signal.direction == Direction.UP
        assert signal.inflation_signal.direction == Direction.DOWN

    def test_clear_stagflation(self) -> None:
        detector = RuleBasedRegimeDetector(
            indicators=[
                _make_indicator("g1", MacroDimension.GROWTH, Direction.DOWN, 0.85),
                _make_indicator("g2", MacroDimension.GROWTH, Direction.DOWN, 0.75),
                _make_indicator("i1", MacroDimension.INFLATION, Direction.UP, 0.85),
                _make_indicator("i2", MacroDimension.INFLATION, Direction.UP, 0.80),
            ],
        )
        signal = detector.detect(as_of=date(2026, 5, 1))
        assert signal.regime == Regime.STAGFLATION

    def test_uncertain_when_dimension_is_neutral(self) -> None:
        detector = RuleBasedRegimeDetector(
            indicators=[
                _make_indicator("g1", MacroDimension.GROWTH, Direction.UP, 0.5),
                _make_indicator("g2", MacroDimension.GROWTH, Direction.DOWN, 0.5),
                _make_indicator("i1", MacroDimension.INFLATION, Direction.UP, 0.85),
            ],
        )
        signal = detector.detect(as_of=date(2026, 5, 1))
        # Growth tied -> NEUTRAL -> regime UNCERTAIN
        assert signal.growth_signal.direction == Direction.NEUTRAL
        assert signal.regime == Regime.UNCERTAIN

    def test_failed_indicator_is_skipped(self) -> None:
        good = _make_indicator("g1", MacroDimension.GROWTH, Direction.UP, 0.85)
        bad = MagicMock(spec=MacroIndicator)
        bad.name = "broken"
        bad.dimension = MacroDimension.GROWTH
        bad.read.side_effect = RuntimeError("FRED is down")

        infl = _make_indicator("i1", MacroDimension.INFLATION, Direction.DOWN, 0.7)
        detector = RuleBasedRegimeDetector(indicators=[good, bad, infl])
        signal = detector.detect(as_of=date(2026, 5, 1))
        assert signal.regime == Regime.GOLDILOCKS
        assert len(signal.growth_signal.contributing_readings) == 1

    def test_missing_dimension_raises(self) -> None:
        # Only growth indicators -> inflation has no readings -> error
        detector = RuleBasedRegimeDetector(
            indicators=[
                _make_indicator("g1", MacroDimension.GROWTH, Direction.UP, 0.85),
            ],
        )
        with pytest.raises(RuntimeError, match="No readings available for dimension"):
            detector.detect(as_of=date(2026, 5, 1))

    def test_no_indicators_raises_at_construction(self) -> None:
        with pytest.raises(ValueError, match="at least one indicator"):
            RuleBasedRegimeDetector(indicators=[])

    def test_combined_confidence_is_min_of_dimensions(self) -> None:
        detector = RuleBasedRegimeDetector(
            indicators=[
                _make_indicator("g1", MacroDimension.GROWTH, Direction.UP, 0.95),
                _make_indicator("i1", MacroDimension.INFLATION, Direction.DOWN, 0.40),
            ],
        )
        signal = detector.detect(as_of=date(2026, 5, 1))
        # growth confidence ~ 0.95, inflation ~ 0.40, combined = min = 0.40
        assert signal.confidence == pytest.approx(0.40, abs=0.01)
