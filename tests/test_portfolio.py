"""Unit tests for the portfolio module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from bml.allocation.models import BucketWeight, TargetAllocation
from bml.portfolio import (
    PortfolioSimulator,
    PortfolioState,
    Position,
    TransactionType,
)
from bml.selection.models import Portfolio, PortfolioPosition
from bml.universe.asset import Asset, AssetClass, Region


def _asset(
    ticker: str,
    isin: str,
    asset_class: AssetClass = AssetClass.EQUITY_DM,
    name: str | None = None,
) -> Asset:
    return Asset(
        ticker=ticker,
        isin=isin,
        name=name or f"Test {ticker}",
        asset_class=asset_class,
        region=Region.GLOBAL,
        currency="USD",
        ter=0.001,
    )


def _make_target(
    positions: list[tuple[str, str, float, AssetClass]],
    as_of: date = date(2026, 5, 1),
) -> Portfolio:
    """Build a Portfolio (selection output) from (ticker, isin, weight, bucket) tuples."""
    p_positions = [
        PortfolioPosition(
            asset=_asset(t, isin, ac),
            weight=w,
            bucket=ac,
            score=1.0,
        )
        for t, isin, w, ac in positions
    ]
    buckets = [BucketWeight(asset_class=ac, weight=w) for _, _, w, ac in positions]
    target_alloc = TargetAllocation(as_of=as_of, buckets=buckets)
    return Portfolio(
        as_of=as_of,
        positions=p_positions,
        target_allocation=target_alloc,
    )


def _flat_prices(tickers: dict[str, float], n_days: int = 60) -> pd.DataFrame:
    """Build a DataFrame of constant prices for testing."""
    dates = pd.date_range(end="2026-05-01", periods=n_days, freq="B")
    return pd.DataFrame({t: [p] * n_days for t, p in tickers.items()}, index=dates)


class TestPositionModel:
    def test_market_value(self) -> None:
        pos = Position(
            asset=_asset("AAA", "IE00000000AA"),
            quantity=10.0,
            cost_basis=50.0,
            current_price=55.0,
            bucket=AssetClass.EQUITY_DM,
        )
        assert pos.market_value == pytest.approx(550.0)
        assert pos.unrealized_pnl == pytest.approx(50.0)
        assert pos.unrealized_pnl_pct == pytest.approx(0.10)


class TestPortfolioStateModel:
    def _state(self) -> PortfolioState:
        return PortfolioState(
            as_of=date(2026, 5, 1),
            inception_date=date(2026, 5, 1),
            inception_value=100_000.0,
            positions=[
                Position(
                    asset=_asset("AAA", "IE00000000AA"),
                    quantity=10.0,
                    cost_basis=50.0,
                    current_price=55.0,
                    bucket=AssetClass.EQUITY_DM,
                ),
                Position(
                    asset=_asset("BBB", "IE00000000BB", AssetClass.GOLD),
                    quantity=20.0,
                    cost_basis=100.0,
                    current_price=110.0,
                    bucket=AssetClass.GOLD,
                ),
            ],
            cash=100.0,
        )

    def test_total_value_includes_cash(self) -> None:
        s = self._state()
        # 10 * 55 = 550 + 20 * 110 = 2200 + 100 cash = 2850
        assert s.total_value == pytest.approx(2850.0)

    def test_total_return(self) -> None:
        s = self._state()
        # invested at inception = 100k, total_value = 2850
        # return = 2850/100000 - 1 = -0.9715
        assert s.total_return == pytest.approx(2850.0 / 100_000.0 - 1.0)

    def test_position_for(self) -> None:
        s = self._state()
        assert s.position_for("AAA") is not None
        assert s.position_for("MISSING") is None

    def test_weight_of(self) -> None:
        s = self._state()
        # AAA market_value = 550, total = 2850
        assert s.weight_of("AAA") == pytest.approx(550.0 / 2850.0)

    def test_total_weight_in_asset_class(self) -> None:
        s = self._state()
        assert s.total_weight_in(AssetClass.GOLD) == pytest.approx(2200.0 / 2850.0)

    def test_negative_cash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioState(
                as_of=date(2026, 5, 1),
                inception_date=date(2026, 5, 1),
                inception_value=1000.0,
                positions=[],
                cash=-50.0,
            )


class TestPortfolioSimulatorInitialize:
    def test_initialize_creates_correct_quantities(self) -> None:
        target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.6, AssetClass.EQUITY_DM),
                ("BBB", "IE00000000BB", 0.4, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0, "BBB": 50.0})

        state = PortfolioSimulator.initialize(
            target=target,
            prices=prices,
            capital=100_000.0,
            as_of=date(2026, 5, 1),
        )

        assert len(state.positions) == 2
        aaa = state.position_for("AAA")
        bbb = state.position_for("BBB")
        assert aaa is not None
        assert bbb is not None
        # AAA: 60k / 100 = 600 shares
        assert aaa.quantity == pytest.approx(600.0)
        # BBB: 40k / 50 = 800 shares
        assert bbb.quantity == pytest.approx(800.0)

    def test_initialize_records_buy_transactions(self) -> None:
        target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        prices = _flat_prices({"AAA": 100.0})
        state = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=10_000.0, as_of=date(2026, 5, 1)
        )
        assert len(state.transactions) == 1
        tx = state.transactions[0]
        assert tx.transaction_type == TransactionType.BUY
        assert tx.quantity == pytest.approx(100.0)
        assert tx.price == pytest.approx(100.0)

    def test_initialize_total_value_equals_capital(self) -> None:
        target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.5, AssetClass.EQUITY_DM),
                ("BBB", "IE00000000BB", 0.5, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0, "BBB": 50.0})
        state = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )
        # No drift, total_value should equal capital
        assert state.total_value == pytest.approx(100_000.0)
        assert state.cash == pytest.approx(0.0, abs=1e-6)

    def test_capital_must_be_positive(self) -> None:
        target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        prices = _flat_prices({"AAA": 100.0})
        with pytest.raises(ValueError, match="positive"):
            PortfolioSimulator.initialize(
                target=target, prices=prices, capital=0.0, as_of=date(2026, 5, 1)
            )

    def test_missing_price_skips_position(self) -> None:
        target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.5, AssetClass.EQUITY_DM),
                ("MISSING", "IE000000MISG", 0.5, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0})  # MISSING not in prices
        state = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )
        assert len(state.positions) == 1
        # Cash holds the unspent amount (50k for the missing bucket)
        assert state.cash == pytest.approx(50_000.0, abs=1e-6)


class TestPortfolioSimulatorUpdateValuations:
    def test_update_changes_market_value(self) -> None:
        target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        # Day 1: price 100. Day 60: price 110.
        dates = pd.date_range(end="2026-05-01", periods=60, freq="B")
        prices = pd.DataFrame(
            {"AAA": [100.0] * 30 + [110.0] * 30},
            index=dates,
        )

        initial_date = dates[0].date()
        later_date = dates[-1].date()

        state0 = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=10_000.0, as_of=initial_date
        )
        state1 = PortfolioSimulator.update_valuations(state0, prices, later_date)

        assert state1.total_value == pytest.approx(11_000.0, rel=1e-6)
        assert state1.total_return == pytest.approx(0.10)
        # No transactions added
        assert len(state1.transactions) == len(state0.transactions)


class TestPortfolioSimulatorRebalance:
    def test_rebalance_to_new_universe(self) -> None:
        old_target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.5, AssetClass.EQUITY_DM),
                ("BBB", "IE00000000BB", 0.5, AssetClass.GOLD),
            ]
        )
        new_target = _make_target(
            [
                ("CCC", "IE00000000CC", 0.6, AssetClass.EQUITY_DM),
                ("DDD", "IE00000000DD", 0.4, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0, "BBB": 50.0, "CCC": 200.0, "DDD": 25.0})

        state0 = PortfolioSimulator.initialize(
            target=old_target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )
        state1 = PortfolioSimulator.rebalance(
            state=state0, target=new_target, prices=prices, as_of=date(2026, 5, 1)
        )

        # AAA and BBB should be sold (not in new target)
        assert state1.position_for("AAA") is None
        assert state1.position_for("BBB") is None
        # CCC and DDD should be in new portfolio
        assert state1.position_for("CCC") is not None
        assert state1.position_for("DDD") is not None
        # Total value preserved (no fees, prices flat)
        assert state1.total_value == pytest.approx(100_000.0, rel=1e-6)

    def test_rebalance_records_transactions(self) -> None:
        old_target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        new_target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.7, AssetClass.EQUITY_DM),
                ("BBB", "IE00000000BB", 0.3, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0, "BBB": 50.0})

        state0 = PortfolioSimulator.initialize(
            target=old_target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )
        state1 = PortfolioSimulator.rebalance(
            state=state0, target=new_target, prices=prices, as_of=date(2026, 5, 1)
        )

        # State1 should have rebalance transactions for AAA (sell some) and BBB (buy)
        rebalance_txs = [
            t for t in state1.transactions if t.transaction_type == TransactionType.REBALANCE
        ]
        assert len(rebalance_txs) >= 2

    def test_rebalance_preserves_inception(self) -> None:
        target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        prices = _flat_prices({"AAA": 100.0})

        state0 = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )
        state1 = PortfolioSimulator.rebalance(
            state=state0, target=target, prices=prices, as_of=date(2026, 5, 8)
        )
        assert state1.inception_date == date(2026, 5, 1)
        assert state1.inception_value == pytest.approx(100_000.0)


class TestPortfolioSimulatorPersistence:
    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        target = _make_target(
            [
                ("AAA", "IE00000000AA", 0.5, AssetClass.EQUITY_DM),
                ("BBB", "IE00000000BB", 0.5, AssetClass.GOLD),
            ]
        )
        prices = _flat_prices({"AAA": 100.0, "BBB": 50.0})
        state = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=100_000.0, as_of=date(2026, 5, 1)
        )

        path = tmp_path / "state.json"
        PortfolioSimulator.save(state, path)
        assert path.exists()

        loaded = PortfolioSimulator.load(path)
        assert loaded.as_of == state.as_of
        assert loaded.inception_value == state.inception_value
        assert len(loaded.positions) == len(state.positions)
        assert loaded.position_for("AAA").quantity == pytest.approx(  # type: ignore[union-attr]
            state.position_for("AAA").quantity  # type: ignore[union-attr]
        )


class TestPortfolioSimulatorPerformance:
    def test_period_return(self) -> None:
        target = _make_target([("AAA", "IE00000000AA", 1.0, AssetClass.EQUITY_DM)])
        # Prices: 100 from day 0 to day 29, then 120 from day 30 to 59
        dates = pd.date_range(end="2026-05-01", periods=60, freq="B")
        prices = pd.DataFrame({"AAA": [100.0] * 30 + [120.0] * 30}, index=dates)

        start_date = dates[0].date()
        end_date = dates[-1].date()

        state0 = PortfolioSimulator.initialize(
            target=target, prices=prices, capital=10_000.0, as_of=start_date
        )
        state1 = PortfolioSimulator.update_valuations(state0, prices, end_date)

        assert PortfolioSimulator.period_return(state0, state1) == pytest.approx(0.20)
