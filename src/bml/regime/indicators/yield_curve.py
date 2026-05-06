"""US Treasury yield curve slope indicator (10Y - 3M).

A negative slope (inverted curve) is one of the most reliable recession
signals in macro economics, leading NBER recessions by 6-12 months.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime.enums import Direction, MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class YieldCurveIndicator(MacroIndicator):
    """10Y - 3M US Treasury yield curve slope (FRED series T10Y3M).

    Decision logic:
    - If absolute value < `inversion_threshold` (default -0.25%), force
      direction = DOWN with high confidence: an inverted curve is a strong
      standalone recession signal regardless of historical distribution.
    - Otherwise, compute z-score vs the trailing `lookback_years` window.
      |z| > 0.5 -> directional, sign of z drives UP (steepening = growth) /
      DOWN (flattening = slowdown). |z| <= 0.5 -> NEUTRAL.
    """

    SERIES_ID = "T10Y3M"
    INVERSION_THRESHOLD = -0.25  # percent
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    Z_THRESHOLD = 0.5

    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "yield_curve_10y3m"

    @property
    def dimension(self) -> MacroDimension:
        return MacroDimension.GROWTH

    def fetch_history(self, end: date) -> pd.Series:
        start = date(end.year - self.HISTORY_YEARS, end.month, end.day)
        return self._provider.fetch_series(self.SERIES_ID, start, end)

    def read(self, as_of: date) -> IndicatorReading:
        history = self.fetch_history(as_of).dropna()
        if history.empty:
            msg = f"No data returned for {self.SERIES_ID} up to {as_of}"
            raise ValueError(msg)

        current_value = float(history.iloc[-1])

        # Inversion override: a negative curve is a strong recession signal.
        if current_value < self.INVERSION_THRESHOLD:
            return IndicatorReading(
                indicator_name=self.name,
                dimension=self.dimension,
                as_of=as_of,
                value=current_value,
                z_score=None,
                direction=Direction.DOWN,
                confidence=0.9,
            )

        # Otherwise, normalize against the trailing window.
        lookback_start = pd.Timestamp(
            date(as_of.year - self.LOOKBACK_YEARS, as_of.month, as_of.day)
        )
        window = history[history.index >= lookback_start]
        if len(window) < 60:  # need at least ~3 months of data
            return IndicatorReading(
                indicator_name=self.name,
                dimension=self.dimension,
                as_of=as_of,
                value=current_value,
                z_score=None,
                direction=Direction.NEUTRAL,
                confidence=0.3,
            )

        mean = float(window.mean())
        std = float(window.std())
        z = 0.0 if std == 0.0 else (current_value - mean) / std

        if z > self.Z_THRESHOLD:
            direction = Direction.UP
            confidence = min(0.5 + abs(z) * 0.2, 0.95)
        elif z < -self.Z_THRESHOLD:
            direction = Direction.DOWN
            confidence = min(0.5 + abs(z) * 0.2, 0.95)
        else:
            direction = Direction.NEUTRAL
            confidence = 0.4

        return IndicatorReading(
            indicator_name=self.name,
            dimension=self.dimension,
            as_of=as_of,
            value=current_value,
            z_score=round(z, 3),
            direction=direction,
            confidence=round(confidence, 2),
        )
