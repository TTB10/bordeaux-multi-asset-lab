"""PortfolioSimulator: stateless lifecycle operations for a portfolio.

All methods are static and produce new immutable PortfolioState objects.
This stateless design makes the module easy to test and reason about.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger

from bml.portfolio.models import (
    PortfolioState,
    Position,
    Transaction,
    TransactionType,
)
from bml.selection.models import Portfolio


class PortfolioSimulator:
    """Stateless lifecycle operations for portfolio paper-trading."""

    @staticmethod
    def initialize(
        target: Portfolio,
        prices: pd.DataFrame,
        capital: float,
        as_of: date,
    ) -> PortfolioState:
        """Build the initial portfolio state from a target allocation.

        Args:
            target: Output of the selection module.
            prices: Historical prices indexed by date, columns by ticker.
            capital: Initial capital in account currency.
            as_of: Reference date for initialization.

        Returns:
            A new PortfolioState representing the inception of the portfolio.
        """
        if capital <= 0.0:
            msg = "Initial capital must be strictly positive"
            raise ValueError(msg)

        positions: list[Position] = []
        transactions: list[Transaction] = []
        spent = 0.0

        for tp in target.positions:
            ticker = tp.asset.ticker
            price = PortfolioSimulator._latest_price_at(prices, ticker, as_of)
            if price is None:
                logger.warning(
                    "No price for {ticker} at {as_of}; skipping in initialization",
                    ticker=ticker,
                    as_of=as_of,
                )
                continue

            target_value = capital * tp.weight
            quantity = target_value / price  # fractional shares allowed in V1
            if quantity <= 0:
                continue

            positions.append(
                Position(
                    asset=tp.asset,
                    quantity=quantity,
                    cost_basis=price,
                    current_price=price,
                    bucket=tp.bucket,
                )
            )
            transactions.append(
                Transaction(
                    as_of=as_of,
                    ticker=ticker,
                    quantity=quantity,
                    price=price,
                    transaction_type=TransactionType.BUY,
                )
            )
            spent += quantity * price

        cash = max(0.0, capital - spent)

        return PortfolioState(
            as_of=as_of,
            inception_date=as_of,
            inception_value=capital,
            positions=positions,
            cash=cash,
            transactions=transactions,
        )

    @staticmethod
    def update_valuations(
        state: PortfolioState,
        prices: pd.DataFrame,
        as_of: date,
    ) -> PortfolioState:
        """Refresh each position's current_price using prices at as_of.

        Quantities and cost basis stay unchanged (no transactions occur).
        Cash is preserved. Used to roll the portfolio forward through time.
        """
        new_positions: list[Position] = []
        for p in state.positions:
            ticker = p.asset.ticker
            new_price = PortfolioSimulator._latest_price_at(prices, ticker, as_of)
            if new_price is None:
                # No new price -> keep last known price
                new_positions.append(p)
                continue
            new_positions.append(
                Position(
                    asset=p.asset,
                    quantity=p.quantity,
                    cost_basis=p.cost_basis,
                    current_price=new_price,
                    bucket=p.bucket,
                )
            )
        return state.model_copy(update={"as_of": as_of, "positions": new_positions})

    @staticmethod
    def rebalance(
        state: PortfolioState,
        target: Portfolio,
        prices: pd.DataFrame,
        as_of: date,
    ) -> PortfolioState:
        """Rebalance the portfolio toward the new target allocation.

        Pipeline:
          1. Update valuations to as_of (so we trade at current prices).
          2. For each existing position not in the new target, generate a SELL.
          3. For each target position, compute the new quantity required and
             generate a BUY/SELL/HOLD with appropriate cost basis update.
          4. Compute residual cash from rounding effects.
        """
        updated = PortfolioSimulator.update_valuations(state, prices, as_of)
        total_value = updated.total_value

        existing_by_ticker: dict[str, Position] = {p.asset.ticker: p for p in updated.positions}
        target_tickers = {tp.asset.ticker for tp in target.positions}

        new_transactions: list[Transaction] = list(updated.transactions)

        # 1. SELL positions that are no longer in target
        for ticker, pos in existing_by_ticker.items():
            if ticker not in target_tickers and pos.quantity > 0:
                new_transactions.append(
                    Transaction(
                        as_of=as_of,
                        ticker=ticker,
                        quantity=-pos.quantity,
                        price=pos.current_price,
                        transaction_type=TransactionType.REBALANCE,
                    )
                )

        # 2. Adjust each target position to new quantity
        new_positions: list[Position] = []
        spent_or_kept = 0.0

        for tp in target.positions:
            ticker = tp.asset.ticker
            price = PortfolioSimulator._latest_price_at(prices, ticker, as_of)
            if price is None:
                logger.warning(
                    "No price for {ticker} on {as_of}; cannot include in rebalance",
                    ticker=ticker,
                    as_of=as_of,
                )
                continue

            target_value = total_value * tp.weight
            new_qty = target_value / price
            existing = existing_by_ticker.get(ticker)

            if existing is None:
                # New position: full buy
                cost_basis = price
                qty_change = new_qty
            else:
                qty_change = new_qty - existing.quantity
                if qty_change > 1e-12:
                    # Buying more: weighted-average cost basis update
                    new_invest = qty_change * price
                    old_invest = existing.quantity * existing.cost_basis
                    cost_basis = (old_invest + new_invest) / new_qty if new_qty > 0 else price
                else:
                    # Selling some or holding: keep cost basis
                    cost_basis = existing.cost_basis

            if abs(qty_change) > 1e-9:
                new_transactions.append(
                    Transaction(
                        as_of=as_of,
                        ticker=ticker,
                        quantity=qty_change,
                        price=price,
                        transaction_type=TransactionType.REBALANCE,
                    )
                )

            new_positions.append(
                Position(
                    asset=tp.asset,
                    quantity=new_qty,
                    cost_basis=cost_basis,
                    current_price=price,
                    bucket=tp.bucket,
                )
            )
            spent_or_kept += new_qty * price

        # 3. Residual cash from rounding
        cash = total_value - spent_or_kept
        if cash < 0 and cash > -1e-6 * total_value:
            cash = 0.0  # absorb floating point drift
        cash = max(0.0, cash)

        return PortfolioState(
            as_of=as_of,
            inception_date=updated.inception_date,
            inception_value=updated.inception_value,
            positions=new_positions,
            cash=cash,
            transactions=new_transactions,
        )

    @staticmethod
    def save(state: PortfolioState, path: str | Path) -> None:
        """Persist the portfolio state to a JSON file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> PortfolioState:
        """Load a portfolio state from a JSON file."""
        return PortfolioState.model_validate_json(Path(path).read_text(encoding="utf-8"))

    @staticmethod
    def period_return(start: PortfolioState, end: PortfolioState) -> float:
        """Return between two states (assumes same inception)."""
        if start.total_value <= 0:
            return 0.0
        return end.total_value / start.total_value - 1.0

    @staticmethod
    def _latest_price_at(prices: pd.DataFrame, ticker: str, as_of: date) -> float | None:
        """Return the most recent price for ticker at or before as_of."""
        if ticker not in prices.columns:
            return None
        series = prices[ticker].dropna()
        if series.empty:
            return None
        cutoff = pd.Timestamp(as_of)
        valid = series[series.index <= cutoff]
        if valid.empty:
            return None
        return float(valid.iloc[-1])
