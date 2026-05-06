"""Abstract base class for regime detection strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from bml.regime.models import RegimeSignal


class RegimeDetector(ABC):
    """Strategy interface for regime detection.

    Implementations may be rule-based, model-based (HMM, clustering),
    or hybrid. They all expose the same `detect()` contract so the rest
    of the framework (allocator, dashboard, reporting) is decoupled
    from the detection logic.
    """

    @abstractmethod
    def detect(self, as_of: date) -> RegimeSignal:
        """Return the regime classification at the given as-of date."""
