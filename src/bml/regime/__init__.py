"""Macro regime detection module.

Implements the Bridgewater 2x2 framework: classify the current macro
environment into one of four regimes based on the cross of growth and
inflation directions.
"""

from bml.regime.aggregators import DimensionAggregator, WeightedVoteAggregator
from bml.regime.detector import RegimeDetector, RuleBasedRegimeDetector
from bml.regime.enums import Direction, MacroDimension, Regime
from bml.regime.indicators import MacroIndicator
from bml.regime.models import DimensionalSignal, IndicatorReading, RegimeSignal

__all__ = [
    "DimensionAggregator",
    "DimensionalSignal",
    "Direction",
    "IndicatorReading",
    "MacroDimension",
    "MacroIndicator",
    "Regime",
    "RegimeDetector",
    "RegimeSignal",
    "RuleBasedRegimeDetector",
    "WeightedVoteAggregator",
]
