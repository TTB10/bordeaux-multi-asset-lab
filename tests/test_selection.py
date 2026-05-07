"""Unit tests for the selection module."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from bml.allocation.models import BucketWeight, TargetAllocation
from bml.selection import (
    CompositeScorer,
    Portfolio,
    PortfolioPosition,
    TopNPerBucketStrategy,
)
from bml.universe import Asset, AssetClass, Region, Universe


def _asset(
    ticker: str,
    isin: str,
    asset_class: AssetClass = AssetClass.EQUITY_DM,
    region: Region = Region.GLOBAL,
    ter: float = 0.002,
    name: str | None = None,
) -> Asset:
    return Asset(
        ticker=ticker,
        isin=isin,
        name=name or f"Test {ticker}",
        asset_class=asset_class,
        region=region,
        currency="USD",
        ter=ter,
    )


def _series(annual_return: float, annual_vol: float, n_days: int = 750, seed: int = 0) -> pd.Series:
    """Build a synthetic price series with target annualised return and vol."""
    rng = np.random.default_rng(seed=seed)
    daily_mu = annual_return / 252.0
    daily_sigma = annual_vol / np.sqrt(252.0)
    log_returns = rng.normal(daily_mu, daily_sigma, size=n_days)
    levels = 100.0 * np.exp(np.cumsum(log_returns))
    dates = pd.date_range(end="2026-05-01", periods=n_days, freq="B")
    return pd.Series(levels, index=dates)


class TestPortfolioPositionModel:
    def test_valid_position(self) -> None:
        a = _asset("CSPX.L", "IE00B5BMR087")
        p = PortfolioPosition(asset=a, weight=0.5, bucket=AssetClass.EQUITY_DM, score=1.2)
        assert p.weight == pytest.approx(0.5)
        assert p.bucket == AssetClass.EQUITY_DM

    def test_position_is_frozen(self) -> None:
        a = _asset("CSPX.L", "IE00B5BMR087")
        p = PortfolioPosition(asset=a, weight=0.5, bucket=AssetClass.EQUITY_DM, score=1.2)
        with pytest.raises(ValidationError):
            p.weight = 0.6


class TestPortfolioModel:
    def _build_portfolio(self) -> Portfolio:
        a1 = _asset("CSPX.L", "IE00B5BMR087")
        a2 = _asset("IGLN.L", "IE00B4ND3602", asset_class=AssetClass.GOLD)
        ta = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.6),
                BucketWeight(asset_class=AssetClass.GOLD, weight=0.4),
            ],
        )
        return Portfolio(
            as_of=date(2026, 5, 1),
            positions=[
                PortfolioPosition(asset=a1, weight=0.6, bucket=AssetClass.EQUITY_DM, score=1.0),
                PortfolioPosition(asset=a2, weight=0.4, bucket=AssetClass.GOLD, score=0.5),
            ],
            target_allocation=ta,
        )

    def test_valid_portfolio(self) -> None:
        p = self._build_portfolio()
        assert len(p.positions) == 2
        assert p.total_weight_in(AssetClass.EQUITY_DM) == pytest.approx(0.6)
        assert p.as_dict() == {"CSPX.L": 0.6, "IGLN.L": 0.4}

    def test_weights_must_sum_to_one(self) -> None:
        a = _asset("CSPX.L", "IE00B5BMR087")
        ta = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=1.0)],
        )
        with pytest.raises(ValidationError, match=r"must sum to 1\.0"):
            Portfolio(
                as_of=date(2026, 5, 1),
                positions=[
                    PortfolioPosition(asset=a, weight=0.5, bucket=AssetClass.EQUITY_DM, score=0.0)
                ],
                target_allocation=ta,
            )

    def test_duplicate_assets_raises(self) -> None:
        a = _asset("CSPX.L", "IE00B5BMR087")
        ta = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=1.0)],
        )
        with pytest.raises(ValidationError, match="Duplicate asset"):
            Portfolio(
                as_of=date(2026, 5, 1),
                positions=[
                    PortfolioPosition(asset=a, weight=0.5, bucket=AssetClass.EQUITY_DM, score=0.0),
                    PortfolioPosition(asset=a, weight=0.5, bucket=AssetClass.EQUITY_DM, score=0.0),
                ],
                target_allocation=ta,
            )


class TestCompositeScorer:
    def test_higher_sharpe_returns_higher_score(self) -> None:
        scorer = CompositeScorer()
        good = _series(annual_return=0.12, annual_vol=0.10, seed=1)
        bad = _series(annual_return=0.02, annual_vol=0.10, seed=2)
        good_metrics = scorer.metrics(good, _asset("GOOD", "IE00AAAAAAAA"))
        bad_metrics = scorer.metrics(bad, _asset("BAD", "IE00BBBBBBBB"))
        assert good_metrics["sharpe"] > bad_metrics["sharpe"]

    def test_lower_ter_returns_higher_neg_ter(self) -> None:
        scorer = CompositeScorer()
        prices = _series(0.05, 0.1, seed=3)
        cheap = scorer.metrics(prices, _asset("CHEAP", "IE00CHEAPXXX", ter=0.0007))
        expensive = scorer.metrics(prices, _asset("EXP", "IE00EXPXXXXX", ter=0.0080))
        assert cheap["neg_ter"] > expensive["neg_ter"]

    def test_short_history_returns_neutral(self) -> None:
        scorer = CompositeScorer()
        short = _series(0.10, 0.10, n_days=30, seed=4)
        m = scorer.metrics(short, _asset("SHORT", "IE00SHORTXXX", ter=0.001))
        assert m["sharpe"] == 0.0
        assert m["neg_drawdown"] == 0.0
        assert m["neg_ter"] == pytest.approx(-0.001)


class TestTopNPerBucketStrategy:
    def _equity_universe(self) -> Universe:
        return Universe(
            [
                _asset("EQA", "IE00EQAXXXXX", AssetClass.EQUITY_DM, ter=0.001),
                _asset("EQB", "IE00EQBXXXXX", AssetClass.EQUITY_DM, ter=0.002),
                _asset("EQC", "IE00EQCXXXXX", AssetClass.EQUITY_DM, ter=0.003),
                _asset("CASH1", "IE00CASH1XXX", AssetClass.CASH, ter=0.0009),
                _asset("CASH2", "IE00CASH2XXX", AssetClass.CASH, ter=0.001),
            ]
        )

    def _equity_prices(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "EQA": _series(0.20, 0.05, seed=10),  # very high Sharpe (clear winner)
                "EQB": _series(0.05, 0.05, seed=11),  # medium Sharpe
                "EQC": _series(-0.10, 0.05, seed=12),  # negative Sharpe (clear loser)
                "CASH1": _series(0.025, 0.005, seed=13),
                "CASH2": _series(0.024, 0.005, seed=14),
            }
        )

    def test_top_n_picks_best_assets(self) -> None:
        strategy = TopNPerBucketStrategy(n_per_bucket=2)
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.7),
                BucketWeight(asset_class=AssetClass.CASH, weight=0.3),
            ],
        )
        portfolio = strategy.select(target, self._equity_universe(), self._equity_prices())

        eq_positions = portfolio.positions_in(AssetClass.EQUITY_DM)
        eq_tickers = {p.asset.ticker for p in eq_positions}
        assert len(eq_positions) == 2
        assert "EQA" in eq_tickers  # best Sharpe must be picked
        assert "EQC" not in eq_tickers  # worst must be skipped

    def test_equal_weight_within_bucket(self) -> None:
        strategy = TopNPerBucketStrategy(n_per_bucket=2)
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.7),
                BucketWeight(asset_class=AssetClass.CASH, weight=0.3),
            ],
        )
        portfolio = strategy.select(target, self._equity_universe(), self._equity_prices())

        eq_positions = portfolio.positions_in(AssetClass.EQUITY_DM)
        for p in eq_positions:
            assert p.weight == pytest.approx(0.35, abs=1e-3)

    def test_total_weight_sums_to_one(self) -> None:
        strategy = TopNPerBucketStrategy()
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.7),
                BucketWeight(asset_class=AssetClass.CASH, weight=0.3),
            ],
        )
        portfolio = strategy.select(target, self._equity_universe(), self._equity_prices())
        total = sum(p.weight for p in portfolio.positions)
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_zero_weight_buckets_ignored(self) -> None:
        strategy = TopNPerBucketStrategy()
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=1.0),
            ],
        )
        portfolio = strategy.select(target, self._equity_universe(), self._equity_prices())
        for p in portfolio.positions:
            assert p.bucket == AssetClass.EQUITY_DM

    def test_missing_bucket_redistributes_to_cash(self) -> None:
        strategy = TopNPerBucketStrategy()
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.5),
                BucketWeight(asset_class=AssetClass.GOLD, weight=0.3),  # not in universe
                BucketWeight(asset_class=AssetClass.CASH, weight=0.2),
            ],
        )
        portfolio = strategy.select(target, self._equity_universe(), self._equity_prices())

        # Gold has no candidates -> 30% should be added to cash
        assert portfolio.total_weight_in(AssetClass.CASH) == pytest.approx(0.5, abs=1e-3)
        assert portfolio.total_weight_in(AssetClass.GOLD) == 0.0
        assert any("gold" in n.lower() for n in portfolio.notes)

    def test_n_per_bucket_validation(self) -> None:
        with pytest.raises(ValueError, match="n_per_bucket"):
            TopNPerBucketStrategy(n_per_bucket=0)

    def test_single_candidate_in_bucket_takes_full_bucket_weight(self) -> None:
        # Universe has only 1 cash asset
        universe = Universe(
            [
                _asset("EQA", "IE00EQAXXXXX", AssetClass.EQUITY_DM, ter=0.001),
                _asset("CASH1", "IE00CASH1XXX", AssetClass.CASH, ter=0.0009),
            ]
        )
        prices = pd.DataFrame(
            {
                "EQA": _series(0.10, 0.10, seed=20),
                "CASH1": _series(0.025, 0.005, seed=21),
            }
        )
        strategy = TopNPerBucketStrategy(n_per_bucket=2)
        target = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.6),
                BucketWeight(asset_class=AssetClass.CASH, weight=0.4),
            ],
        )
        portfolio = strategy.select(target, universe, prices)

        cash_positions = portfolio.positions_in(AssetClass.CASH)
        assert len(cash_positions) == 1
        assert cash_positions[0].weight == pytest.approx(0.4, abs=1e-3)
