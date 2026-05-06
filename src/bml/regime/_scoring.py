"""Reusable scoring helpers for macro indicators.

Most indicators follow the same pattern:
  1. Fetch a long history.
  2. Apply a transformation (YoY change, smoothing, etc.).
  3. Compute a z-score over a trailing lookback window.
  4. Map (z, threshold) -> (Direction, confidence).

This module implements step 4, plus a thin wrapper for step 3.
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple

import pandas as pd

from bml.regime.enums import Direction


class ZScoreSignal(NamedTuple):
    """Output of `compute_zscore_signal`."""

    direction: Direction
    z_score: float | None
    confidence: float
    current_value: float


def compute_zscore_signal(
    history: pd.Series,
    as_of: date,
    lookback_years: int,
    z_threshold: float = 0.5,
    min_observations: int = 30,
    invert_sign: bool = False,
) -> ZScoreSignal:
    """Reduce a time series to a directional signal.

    Args:
        history: Time series indexed by date.
        as_of: Reference date for the latest reading.
        lookback_years: Window length used to compute the z-score.
        z_threshold: |z| above this -> directional, otherwise NEUTRAL.
        min_observations: Minimum points required in the lookback window.
        invert_sign: When True, a high reading maps to DOWN (e.g. for
            unemployment claims where rising claims signal weakening growth).

    Returns:
        A ZScoreSignal with direction, raw z-score (or None if not computed),
        confidence in [0, 1], and the current value of the series.

    Raises:
        ValueError: If history is empty after dropping NaN.
    """
    history = history.dropna()
    if history.empty:
        msg = "history is empty after dropping NaN"
        raise ValueError(msg)

    current_value = float(history.iloc[-1])

    lookback_start = pd.Timestamp(date(as_of.year - lookback_years, as_of.month, as_of.day))
    window = history[history.index >= lookback_start]

    if len(window) < min_observations:
        return ZScoreSignal(Direction.NEUTRAL, None, 0.3, current_value)

    mean = float(window.mean())
    std = float(window.std())
    z = 0.0 if std == 0.0 else (current_value - mean) / std

    # For indicators where high = weak growth (e.g. jobless claims),
    # flip the sign so that "above mean" maps to DOWN.
    effective_z = -z if invert_sign else z

    if effective_z > z_threshold:
        direction = Direction.UP
        confidence = min(0.5 + abs(effective_z) * 0.2, 0.95)
    elif effective_z < -z_threshold:
        direction = Direction.DOWN
        confidence = min(0.5 + abs(effective_z) * 0.2, 0.95)
    else:
        direction = Direction.NEUTRAL
        confidence = 0.4

    return ZScoreSignal(
        direction=direction,
        z_score=round(z, 3),
        confidence=round(confidence, 2),
        current_value=current_value,
    )
