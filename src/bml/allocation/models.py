"""Domain models for portfolio target allocations."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bml.universe.asset import AssetClass


class BucketWeight(BaseModel):
    """Target weight for a single asset class bucket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_class: AssetClass
    weight: float = Field(ge=0.0, le=1.0)


class TargetAllocation(BaseModel):
    """A complete portfolio allocation: weights by asset class summing to 1.0.

    Attributes:
        as_of: Reference date when this allocation was computed.
        buckets: List of BucketWeight, no duplicate AssetClass.
        regime_label: Optional human-readable label for the source regime.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    buckets: list[BucketWeight] = Field(min_length=1)
    regime_label: str | None = None

    @model_validator(mode="after")
    def _check_unique_buckets(self) -> TargetAllocation:
        seen: set[AssetClass] = set()
        for b in self.buckets:
            if b.asset_class in seen:
                msg = f"Duplicate asset class in allocation: {b.asset_class}"
                raise ValueError(msg)
            seen.add(b.asset_class)
        return self

    @model_validator(mode="after")
    def _check_weights_sum_to_one(self) -> TargetAllocation:
        total = sum(b.weight for b in self.buckets)
        if abs(total - 1.0) > 1e-6:
            msg = f"Weights must sum to 1.0, got {total:.6f}"
            raise ValueError(msg)
        return self

    def weight_of(self, asset_class: AssetClass) -> float:
        """Return the weight of `asset_class` in the allocation, 0.0 if absent."""
        for b in self.buckets:
            if b.asset_class == asset_class:
                return b.weight
        return 0.0

    def as_dict(self) -> dict[AssetClass, float]:
        """Return the allocation as a {AssetClass: weight} dict."""
        return {b.asset_class: b.weight for b in self.buckets}
