"""Abstract base class for macroeconomic time-series providers.

Distinct from `DataProvider` (which fetches asset prices), this interface
exposes a `fetch_series` method for individual macro series identified by
a vendor-specific id (e.g. FRED series id like 'T10Y3M').
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class MacroDataProviderError(RuntimeError):
    """Raised when a MacroDataProvider fails to retrieve a series."""


class MacroDataProvider(ABC):
    """Strategy interface for macroeconomic data retrieval."""

    @abstractmethod
    def fetch_series(
        self,
        series_id: str,
        start: date,
        end: date,
    ) -> pd.Series:
        """Fetch a single macro time series.

        Args:
            series_id: Vendor-specific identifier (e.g. 'T10Y3M' for FRED).
            start: Inclusive start date.
            end: Inclusive end date.

        Returns:
            A pandas Series indexed by date with the series values.

        Raises:
            MacroDataProviderError: On any upstream failure.
        """
