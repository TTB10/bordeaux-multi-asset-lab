"""US Core CPI YoY change indicator.

CPILFESL is a monthly FRED series for Core CPI (CPI excluding food and
energy). We track its year-on-year percentage change as a proxy for
underlying inflation pressure.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime._scoring import compute_zscore_signal
from bml.regime.enums import MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class CoreCPIIndicator(MacroIndicator):
    """US Core CPI YoY change (FRED series CPILFESL)."""

    SERIES_ID = "CPILFESL"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    YOY_PERIODS = 12  # monthly data -> 12-period change = YoY

    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "core_cpi_yoy"

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

        yoy = raw.pct_change(periods=self.YOY_PERIODS).dropna() * 100.0

        signal = compute_zscore_signal(
            yoy,
            as_of=as_of,
            lookback_years=self.LOOKBACK_YEARS,
            min_observations=24,
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
