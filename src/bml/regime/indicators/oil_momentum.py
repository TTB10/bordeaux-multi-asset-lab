"""Brent crude oil 6-month momentum indicator.

DCOILBRENTEU is a daily FRED series for Brent crude oil prices.
A sustained positive 6-month momentum signals upcoming inflation pressure
through energy pass-through into headline CPI and producer prices.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime._scoring import compute_zscore_signal
from bml.regime.enums import MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class OilMomentumIndicator(MacroIndicator):
    """Brent oil 6-month momentum (FRED series DCOILBRENTEU)."""

    SERIES_ID = "DCOILBRENTEU"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    MOMENTUM_DAYS = 126  # ~6 months of trading days

    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "brent_oil_6m_momentum"

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

        momentum = (raw.pct_change(periods=self.MOMENTUM_DAYS) * 100.0).dropna()

        signal = compute_zscore_signal(
            momentum,
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
