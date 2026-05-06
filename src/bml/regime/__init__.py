"""Macro regime detection module.

Implements the Bridgewater 2x2 framework: classify the current macro
environment into one of four regimes based on the cross of growth and
inflation directions.
"""

from bml.regime.detector import RegimeDetector
from bml.regime.enums import Direction, MacroDimension, Regime
from bml.regime.indicators import MacroIndicator
from bml.regime.models import DimensionalSignal, IndicatorReading, RegimeSignal

__all__ = [
    "DimensionalSignal",
    "Direction",
    "IndicatorReading",
    "MacroDimension",
    "MacroIndicator",
    "Regime",
    "RegimeDetector",
    "RegimeSignal",
]
