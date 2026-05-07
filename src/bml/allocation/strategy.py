"""Allocation strategies: turn a RegimeSignal into a TargetAllocation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from bml.allocation.models import BucketWeight, TargetAllocation
from bml.allocation.tilts import DEFAULT_REGIME_TILTS, NEUTRAL_TILT
from bml.regime.enums import Regime
from bml.regime.models import RegimeSignal
from bml.universe.asset import AssetClass


class AllocationStrategy(ABC):
    """Strategy interface for computing target allocations."""

    @abstractmethod
    def compute(self, signal: RegimeSignal) -> TargetAllocation:
        """Compute a TargetAllocation from a RegimeSignal."""


class RegimeBasedTacticalStrategy(AllocationStrategy):
    """Map regime to tactical tilts, smoothed by confidence.

    Two-step procedure:
      1. Look up the target tilt for the detected regime.
      2. Interpolate linearly between NEUTRAL_TILT and the regime tilt
         using the signal's confidence as the blending weight.

    Result: at confidence 0 the allocation is fully neutral; at confidence 1
    it is fully aligned with the regime's tilt. This is graceful: the
    portfolio never makes large bets when conviction is low.

    UNCERTAIN regime always returns the neutral allocation regardless of
    the (typically low) confidence.
    """

    def __init__(
        self,
        regime_tilts: dict[Regime, dict[AssetClass, float]] | None = None,
        neutral_tilt: dict[AssetClass, float] | None = None,
    ) -> None:
        self._tilts = regime_tilts if regime_tilts is not None else DEFAULT_REGIME_TILTS
        self._neutral = neutral_tilt if neutral_tilt is not None else NEUTRAL_TILT
        self._validate_tilts()

    def _validate_tilts(self) -> None:
        if abs(sum(self._neutral.values()) - 1.0) > 1e-6:
            msg = "Neutral tilt weights must sum to 1.0"
            raise ValueError(msg)
        for regime, tilt in self._tilts.items():
            total = sum(tilt.values())
            if abs(total - 1.0) > 1e-6:
                msg = f"Tilt for {regime} must sum to 1.0, got {total:.6f}"
                raise ValueError(msg)

    def compute(self, signal: RegimeSignal) -> TargetAllocation:
        if signal.regime == Regime.UNCERTAIN or signal.regime not in self._tilts:
            return self._build(self._neutral, signal.as_of, signal.regime.value)

        target = self._tilts[signal.regime]
        smoothed = self._interpolate(self._neutral, target, signal.confidence)
        return self._build(smoothed, signal.as_of, signal.regime.value)

    @staticmethod
    def _interpolate(
        neutral: dict[AssetClass, float],
        target: dict[AssetClass, float],
        confidence: float,
    ) -> dict[AssetClass, float]:
        """Linear blend: confidence * target + (1 - confidence) * neutral."""
        all_classes = set(neutral) | set(target)
        return {
            ac: round(
                (1.0 - confidence) * neutral.get(ac, 0.0) + confidence * target.get(ac, 0.0),
                6,
            )
            for ac in all_classes
        }

    @staticmethod
    def _build(
        weights: dict[AssetClass, float],
        as_of: date,
        regime_label: str,
    ) -> TargetAllocation:
        # Drop zero weights for cleaner output, then renormalise to handle
        # any floating-point drift introduced by interpolation rounding.
        nonzero = {ac: w for ac, w in weights.items() if w > 1e-9}
        total = sum(nonzero.values())
        if total > 0:
            nonzero = {ac: w / total for ac, w in nonzero.items()}
        buckets = [BucketWeight(asset_class=ac, weight=w) for ac, w in nonzero.items()]
        return TargetAllocation(as_of=as_of, buckets=buckets, regime_label=regime_label)
