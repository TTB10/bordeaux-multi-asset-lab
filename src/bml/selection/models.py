"""Domain models for portfolio construction (output of the selection module)."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bml.allocation.models import TargetAllocation
from bml.universe.asset import Asset, AssetClass


class PortfolioPosition(BaseModel):
    """A single position in the constructed portfolio.

    Attributes:
        asset: The underlying fund / ETF.
        weight: Final weight in the portfolio, in [0, 1].
        bucket: The asset class this position fills (for traceability).
        score: Composite score from the selection scorer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset: Asset
    weight: float = Field(ge=0.0, le=1.0)
    bucket: AssetClass
    score: float


class Portfolio(BaseModel):
    """A tradable portfolio: positions sum to 1.0, no duplicate assets.

    Attributes:
        as_of: Reference date for the construction.
        positions: List of PortfolioPosition. Weights sum to 1.0.
        target_allocation: Source allocation used to construct this portfolio.
        notes: Human-readable notes (e.g. bucket redistributions).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    positions: list[PortfolioPosition] = Field(min_length=1)
    target_allocation: TargetAllocation
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_assets(self) -> Self:
        seen: set[str] = set()
        for p in self.positions:
            if p.asset.isin in seen:
                msg = f"Duplicate asset in portfolio: {p.asset.isin}"
                raise ValueError(msg)
            seen.add(p.asset.isin)
        return self

    @model_validator(mode="after")
    def _check_weights_sum_to_one(self) -> Self:
        total = sum(p.weight for p in self.positions)
        if abs(total - 1.0) > 1e-4:
            msg = f"Portfolio weights must sum to 1.0, got {total:.6f}"
            raise ValueError(msg)
        return self

    def total_weight_in(self, asset_class: AssetClass) -> float:
        """Sum of weights of all positions in the given asset class."""
        return sum(p.weight for p in self.positions if p.bucket == asset_class)

    def positions_in(self, asset_class: AssetClass) -> list[PortfolioPosition]:
        """All positions assigned to the given asset class."""
        return [p for p in self.positions if p.bucket == asset_class]

    def as_dict(self) -> dict[str, float]:
        """Return positions as a {ticker: weight} mapping."""
        return {p.asset.ticker: p.weight for p in self.positions}
