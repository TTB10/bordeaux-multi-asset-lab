"""US Initial Jobless Claims indicator (4-week moving average).

ICSA is a weekly series. Rising claims signal labor market weakening
(growth DOWN), falling claims signal strength (growth UP). The sign
inversion is handled via the `invert_sign` flag in the scoring helper.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bml.data.providers.macro_base import MacroDataProvider
from bml.regime._scoring import compute_zscore_signal
from bml.regime.enums import MacroDimension
from bml.regime.indicators.base import MacroIndicator
from bml.regime.models import IndicatorReading


class JoblessClaimsIndicator(MacroIndicator):
    """US Initial Jobless Claims 4-week MA (FRED series ICSA).

    Decision logic via the scoring helper with `invert_sign=True`:
    a reading meaningfully above the 5y average maps to growth DOWN.
    """

    SERIES_ID = "ICSA"
    LOOKBACK_YEARS = 5
    HISTORY_YEARS = 30
    SMOOTHING_WEEKS = 4

    def __init__(self, provider: MacroDataProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "initial_jobless_claims_4wk_ma"

    @property
    def dimension(self) -> MacroDimension:
        return MacroDimension.GROWTH

    def fetch_history(self, end: date) -> pd.Series:
        start = date(end.year - self.HISTORY_YEARS, end.month, end.day)
        return self._provider.fetch_series(self.SERIES_ID, start, end)

    def read(self, as_of: date) -> IndicatorReading:
        raw = self.fetch_history(as_of).dropna()
        if raw.empty:
            msg = f"No data returned for {self.SERIES_ID} up to {as_of}"
            raise ValueError(msg)

        smoothed = raw.rolling(self.SMOOTHING_WEEKS).mean().dropna()

        signal = compute_zscore_signal(
            smoothed,
            as_of=as_of,
            lookback_years=self.LOOKBACK_YEARS,
            min_observations=12,  # ~3 months of weekly data
            invert_sign=True,
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
