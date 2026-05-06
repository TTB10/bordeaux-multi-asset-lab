"""Enumerations for the regime detection module."""

from __future__ import annotations

from enum import StrEnum


class Direction(StrEnum):
    """Direction of a macro variable: rising, falling, or unclear."""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class MacroDimension(StrEnum):
    """The two axes of the Bridgewater 2x2 framework."""

    GROWTH = "growth"
    INFLATION = "inflation"


class Regime(StrEnum):
    """Macro regime defined by the cross of growth and inflation directions.

    Values match the four quadrants of the Bridgewater 2x2 framework, plus
    an UNCERTAIN state used when at least one dimension is NEUTRAL.
    """

    GOLDILOCKS = "goldilocks"
    REFLATION = "reflation"
    DISINFLATION_RECESSION = "disinflation_recession"
    STAGFLATION = "stagflation"
    UNCERTAIN = "uncertain"

    @classmethod
    def from_directions(
        cls,
        growth: Direction,
        inflation: Direction,
    ) -> Regime:
        """Map a (growth, inflation) directional pair to a regime.

        Returns UNCERTAIN if either input is NEUTRAL.
        """
        if growth == Direction.NEUTRAL or inflation == Direction.NEUTRAL:
            return cls.UNCERTAIN
        if growth == Direction.UP and inflation == Direction.DOWN:
            return cls.GOLDILOCKS
        if growth == Direction.UP and inflation == Direction.UP:
            return cls.REFLATION
        if growth == Direction.DOWN and inflation == Direction.DOWN:
            return cls.DISINFLATION_RECESSION
        if growth == Direction.DOWN and inflation == Direction.UP:
            return cls.STAGFLATION
        msg = f"Unreachable: growth={growth}, inflation={inflation}"
        raise ValueError(msg)
