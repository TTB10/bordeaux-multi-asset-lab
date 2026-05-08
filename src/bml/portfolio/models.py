"""Domain models for portfolio state, positions, and transactions."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from bml.universe.asset import Asset, AssetClass


class TransactionType(StrEnum):
    """Type of portfolio transaction."""

    BUY = "buy"
    SELL = "sell"
    REBALANCE = "rebalance"


class Position(BaseModel):
    """A single holding in the portfolio at a specific point in time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset: Asset
    quantity: float = Field(ge=0.0)
    cost_basis: float = Field(gt=0.0)  # weighted average buy price
    current_price: float = Field(gt=0.0)
    bucket: AssetClass

    @property
    def market_value(self) -> float:
        """Current market value of the position."""
        return self.quantity * self.current_price

    @property
    def cost_value(self) -> float:
        """Total amount invested at cost basis."""
        return self.quantity * self.cost_basis

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit or loss."""
        return self.market_value - self.cost_value

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized P&L as a percentage of cost basis."""
        if self.cost_basis <= 0:
            return 0.0
        return self.current_price / self.cost_basis - 1.0


class Transaction(BaseModel):
    """A buy or sell transaction recorded in portfolio history."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    ticker: str
    quantity: float  # positive = buy, negative = sell
    price: float = Field(gt=0.0)
    transaction_type: TransactionType

    @property
    def notional(self) -> float:
        """Cash impact of the transaction (signed)."""
        return self.quantity * self.price


class PortfolioState(BaseModel):
    """Complete snapshot of the portfolio at a given date."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    inception_date: date
    inception_value: float = Field(gt=0.0)
    positions: list[Position] = Field(default_factory=list)
    cash: float = Field(ge=0.0)
    transactions: list[Transaction] = Field(default_factory=list)

    @property
    def total_value(self) -> float:
        """Total portfolio value: market value of positions + cash."""
        return sum(p.market_value for p in self.positions) + self.cash

    @property
    def invested_value(self) -> float:
        """Market value of positions only (excludes cash)."""
        return sum(p.market_value for p in self.positions)

    @property
    def nav_per_share(self) -> float:
        """NAV indexed on base 100 at inception. Useful for time series."""
        return 100.0 * self.total_value / self.inception_value

    @property
    def total_return(self) -> float:
        """Cumulative return since inception, as a fraction (0.05 = +5%)."""
        return self.total_value / self.inception_value - 1.0

    def position_for(self, ticker: str) -> Position | None:
        """Return the position for a given ticker, or None."""
        for p in self.positions:
            if p.asset.ticker == ticker:
                return p
        return None

    def weight_of(self, ticker: str) -> float:
        """Return the current weight of a ticker in the portfolio."""
        pos = self.position_for(ticker)
        if pos is None or self.total_value <= 0:
            return 0.0
        return pos.market_value / self.total_value

    def total_weight_in(self, asset_class: AssetClass) -> float:
        """Total weight of all positions in an asset class."""
        if self.total_value <= 0:
            return 0.0
        invested = sum(p.market_value for p in self.positions if p.bucket == asset_class)
        return invested / self.total_value
