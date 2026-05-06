"""Regime detection strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from loguru import logger

from bml.regime.aggregators import DimensionAggregator, WeightedVoteAggregator
from bml.regime.enums import MacroDimension, Regime
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import DimensionalSignal, IndicatorReading, RegimeSignal


class RegimeDetector(ABC):
    """Strategy interface for regime detection.

    Implementations may be rule-based, model-based (HMM, clustering),
    or hybrid. They all expose the same `detect()` contract so the rest
    of the framework (allocator, dashboard, reporting) is decoupled
    from the detection logic.
    """

    @abstractmethod
    def detect(self, as_of: date) -> RegimeSignal:
        """Return the regime classification at the given as-of date."""


class RuleBasedRegimeDetector(RegimeDetector):
    """Compose indicators + aggregator into a 2x2 regime classifier.

    Pipeline:
        1. For each indicator, produce an IndicatorReading.
        2. Group readings by dimension.
        3. Aggregate each dimension into a DimensionalSignal.
        4. Map (growth_dir, inflation_dir) -> Regime.

    Indicators that fail (network, missing data) are logged and skipped.
    The detector still produces a RegimeSignal as long as at least one
    indicator from each dimension succeeded.
    """

    def __init__(
        self,
        indicators: list[MacroIndicator],
        aggregator: DimensionAggregator | None = None,
    ) -> None:
        if not indicators:
            msg = "RuleBasedRegimeDetector requires at least one indicator"
            raise ValueError(msg)
        self._indicators = list(indicators)
        self._aggregator: DimensionAggregator = aggregator or WeightedVoteAggregator()

    def detect(self, as_of: date) -> RegimeSignal:
        readings_by_dim: dict[MacroDimension, list[IndicatorReading]] = {
            MacroDimension.GROWTH: [],
            MacroDimension.INFLATION: [],
        }

        for indicator in self._indicators:
            try:
                reading = indicator.read(as_of)
                readings_by_dim[reading.dimension].append(reading)
            except Exception as exc:
                logger.warning(
                    "Indicator '{name}' failed on {as_of}: {exc}",
                    name=indicator.name,
                    as_of=as_of,
                    exc=exc,
                )

        for dim, readings in readings_by_dim.items():
            if not readings:
                msg = (
                    f"No readings available for dimension {dim} on {as_of}; cannot classify regime."
                )
                raise RuntimeError(msg)

        growth_signal = self._aggregator.aggregate(
            readings_by_dim[MacroDimension.GROWTH],
            MacroDimension.GROWTH,
            as_of,
        )
        inflation_signal = self._aggregator.aggregate(
            readings_by_dim[MacroDimension.INFLATION],
            MacroDimension.INFLATION,
            as_of,
        )

        regime = Regime.from_directions(growth_signal.direction, inflation_signal.direction)
        confidence = self._combine_confidence(growth_signal, inflation_signal)

        return RegimeSignal(
            as_of=as_of,
            regime=regime,
            growth_signal=growth_signal,
            inflation_signal=inflation_signal,
            confidence=round(confidence, 3),
        )

    @staticmethod
    def _combine_confidence(
        growth: DimensionalSignal,
        inflation: DimensionalSignal,
    ) -> float:
        """Conservative aggregate: the lower of the two dimensional confidences.

        Rationale: a regime classification is only as reliable as its weakest
        leg. If growth is read with 0.9 conviction but inflation with 0.2,
        we should not advertise 0.9 confidence in the resulting regime.
        """
        return min(growth.confidence, inflation.confidence)
