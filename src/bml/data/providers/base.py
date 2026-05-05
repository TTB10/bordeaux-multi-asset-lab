"""Abstract base class for all market data providers.

The DataProvider interface decouples the rest of the codebase from any
specific data source. To support a new vendor (Bloomberg, Refinitiv, etc.)
implement this interface and inject it where needed - no other module
needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataProvider(ABC):
    """Strategy interface for market price data retrieval."""

    @abstractmethod
    def fetch_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        """Fetch adjusted close prices for the given tickers.

        Args:
            tickers: List of provider-specific tickers.
            start: Inclusive start date.
            end: Inclusive end date.

        Returns:
            A DataFrame indexed by date (DatetimeIndex), with one column per
            ticker. Missing values are forward-filled by the caller, not here.

        Raises:
            DataProviderError: On network failure, empty response, or any
                upstream error. Implementations must wrap vendor-specific
                exceptions into this type.
        """


class DataProviderError(RuntimeError):
    """Raised when a DataProvider fails to retrieve requested data."""
