"""5-year, 5-year forward inflation expectation indicator.

T5YIFR is a daily FRED series representing the market-implied inflation
expectation for the period from 5 to 10 years ahead, derived from the
TIPS-Treasury spread. It is a clean, forward-looking gauge of long-term
inflation expectations - the variable the Fed cares most about anchoring.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime._scoring import compute_zscore_signal
from bml.regime.enums import MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class InflationBreakevenIndicator(MacroIndicator):
    """5y5y forward inflation breakeven (FRED series T5YIFR)."""

    SERIES_ID = "T5YIFR"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30

    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "inflation_breakeven_5y5y"

    @property
    def dimension(self) -> MacroDimension:
        return MacroDimension.INFLATION

    def fetch_history(self, end: date) -> pd.Series:
        start = date(end.year - self.HISTORY_YEARS, end.month, end.day)
        return self._provider.fetch_series(self.SERIES_ID, start, end)

    def read(self, as_of: date) -> IndicatorReading:
        raw = self.fetch_history(as_of).dropna()
        if raw.empty:
            msg = f"No data returned for {self.SERIES_ID} up to {as_of}"
            raise ValueError(msg)

        signal = compute_zscore_signal(
            raw,
            as_of=as_of,
            lookback_years=self.LOOKBACK_YEARS,
            min_observations=60,
        )

        return IndicatorReading(
            indicator_name=self.name,
            dimension=self.dimension,
            as_of=as_of,
            value=signal.current_value,
            z_score=signal.z_score,
            direction=signal.direction,
            confidence=signal.confidence,
        )
