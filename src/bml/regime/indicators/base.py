"""Abstract base class for all macro indicators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from bml.regime.enums import MacroDimension
from bml.regime.models import IndicatorReading


class MacroIndicator(ABC):
    """Strategy interface for any macro indicator.

    An indicator wraps a single underlying time series and exposes:
    - A history fetch (to allow batch backtesting)
    - A point-in-time read (to produce an IndicatorReading at a given date)

    To add a new indicator (e.g. ECB CISS, Citi Inflation Surprise) implement
    this class. No other module needs to change.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short, stable identifier (e.g. 'yield_curve_10y3m')."""

    @property
    @abstractmethod
    def dimension(self) -> MacroDimension:
        """Which macro dimension this indicator informs."""

    @abstractmethod
    def fetch_history(self, end: date) -> pd.Series:
        """Return the indicator's full historical series up to `end`."""

    @abstractmethod
    def read(self, as_of: date) -> IndicatorReading:
        """Produce a structured reading at the given as-of date."""
