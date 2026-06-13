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

    def with_current_price(self, new_price: float) -> "Position":
        """Return a new Position with updated current_price.

        Since Position is frozen=True, we cannot mutate in place.
        This method returns a new instance, leaving cost_basis untouched
        (only current_price is updated, reflecting the latest market price).

        Args:
            new_price: The new current market price.

        Returns:
            A new Position instance with updated current_price.
        """
        if new_price <= 0:
            raise ValueError(f"new_price must be positive, got {new_price}")
        return Position(
            asset=self.asset,
            quantity=self.quantity,
            cost_basis=self.cost_basis,
            current_price=new_price,
            bucket=self.bucket,
        )


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

    def revalue(self, price_dict: dict[str, float], as_of: date) -> "PortfolioState":
        """Return a new PortfolioState with positions revalued at current prices.

        This is the mark-to-market operation. Cost basis is preserved (since
        positions are not re-bought), only current_price is updated.

        Args:
            price_dict: Mapping ticker -> current price.
            as_of: The valuation date (typically today).

        Returns:
            A new PortfolioState with revalued positions.

        Notes:
            - Tickers not in price_dict keep their previous current_price
              (this is the safe fallback: avoid silently dropping positions
              when a single ticker fails to fetch).
            - Cash is unchanged (no interest accrual in V1).
            - Transactions are preserved.
        """
        new_positions = []
        for pos in self.positions:
            ticker = pos.asset.ticker
            if ticker in price_dict and price_dict[ticker] > 0:
                new_positions.append(pos.with_current_price(price_dict[ticker]))
            else:
                # Fallback: keep the previous price if we can't fetch a new one
                new_positions.append(pos)

        return PortfolioState(
            as_of=as_of,
            inception_date=self.inception_date,
            inception_value=self.inception_value,
            positions=new_positions,
            cash=self.cash,
            transactions=list(self.transactions),
        )
