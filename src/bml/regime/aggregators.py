"""Aggregators turn a list of IndicatorReading into a single DimensionalSignal.

The aggregator is the second stage of the regime pipeline:
    IndicatorReading[] -> [DimensionAggregator] -> DimensionalSignal

Each strategy implements a different way of combining individual signals.
The default V1 strategy is a confidence-weighted vote.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from bml.regime.enums import Direction, MacroDimension
from bml.regime.models import DimensionalSignal, IndicatorReading


class DimensionAggregator(ABC):
    """Strategy interface for aggregating indicator readings of one dimension."""

    @abstractmethod
    def aggregate(
        self,
        readings: list[IndicatorReading],
        dimension: MacroDimension,
        as_of: date,
    ) -> DimensionalSignal:
        """Return a single DimensionalSignal summarising all readings.

        Args:
            readings: List of IndicatorReading. All must share `dimension`.
            dimension: The macro dimension being aggregated.
            as_of: Reference date.

        Returns:
            A DimensionalSignal with direction, score in [-1, 1] and confidence.

        Raises:
            ValueError: If `readings` is empty or contains mixed dimensions.
        """


class WeightedVoteAggregator(DimensionAggregator):
    """Confidence-weighted vote over indicator readings.

    Each reading contributes:
        +confidence  if direction is UP
        -confidence  if direction is DOWN
         0           if direction is NEUTRAL

    The aggregate score is the sum divided by the maximum possible weight
    (sum of all confidences). The result lives in [-1, +1].

    Direction mapping:
        score >  +score_threshold -> UP
        score <  -score_threshold -> DOWN
        |score| <= score_threshold -> NEUTRAL

    The aggregate confidence is the absolute value of the score, capped at 1.
    """

    def __init__(self, score_threshold: float = 0.3) -> None:
        if not 0.0 <= score_threshold <= 1.0:
            msg = "score_threshold must be in [0, 1]"
            raise ValueError(msg)
        self._threshold = score_threshold

    def aggregate(
        self,
        readings: list[IndicatorReading],
        dimension: MacroDimension,
        as_of: date,
    ) -> DimensionalSignal:
        if not readings:
            msg = f"Cannot aggregate empty readings list for {dimension}"
            raise ValueError(msg)

        wrong_dim = [r for r in readings if r.dimension != dimension]
        if wrong_dim:
            msg = (
                f"Readings include {len(wrong_dim)} entries not in dimension "
                f"{dimension}: {[r.indicator_name for r in wrong_dim]}"
            )
            raise ValueError(msg)

        total_weight = sum(r.confidence for r in readings)
        if total_weight == 0.0:
            return DimensionalSignal(
                dimension=dimension,
                as_of=as_of,
                direction=Direction.NEUTRAL,
                score=0.0,
                confidence=0.0,
                contributing_readings=readings,
            )

        weighted_sum = 0.0
        for r in readings:
            if r.direction == Direction.UP:
                weighted_sum += r.confidence
            elif r.direction == Direction.DOWN:
                weighted_sum -= r.confidence

        score = max(-1.0, min(1.0, weighted_sum / total_weight))
        mean_confidence = total_weight / len(readings)

        if score > self._threshold:
            direction = Direction.UP
        elif score < -self._threshold:
            direction = Direction.DOWN
        else:
            direction = Direction.NEUTRAL

        # Aggregate confidence reflects BOTH directional clarity (|score|)
        # and the average individual signal quality. Either being weak should
        # pull the aggregate down. A single high-confidence indicator can
        # never produce a 100% aggregate by itself.
        combined_confidence = abs(score) * mean_confidence

        return DimensionalSignal(
            dimension=dimension,
            as_of=as_of,
            direction=direction,
            score=round(score, 3),
            confidence=round(combined_confidence, 3),
            contributing_readings=readings,
        )
