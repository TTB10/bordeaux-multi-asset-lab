"""Unit tests for the Universe domain model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bml.universe import Asset, AssetClass, Region, Universe


def make_asset(
    ticker: str = "IWDA.AS",
    isin: str = "IE00B4L5Y983",
    name: str = "iShares Core MSCI World",
    asset_class: AssetClass = AssetClass.EQUITY_DM,
    region: Region = Region.GLOBAL,
    currency: str = "USD",
    ter: float = 0.0020,
) -> Asset:
    return Asset(
        ticker=ticker,
        isin=isin,
        name=name,
        asset_class=asset_class,
        region=region,
        currency=currency,
        ter=ter,
    )


class TestAsset:
    def test_valid_asset(self) -> None:
        a = make_asset()
        assert a.ticker == "IWDA.AS"
        assert a.isin == "IE00B4L5Y983"

    def test_asset_is_frozen(self) -> None:
        a = make_asset()
        with pytest.raises(ValidationError):
            a.ticker = "OTHER"

    def test_invalid_isin_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_asset(isin="TOO_SHORT")

    def test_invalid_currency_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_asset(currency="usd")  # lowercase rejected

    def test_negative_ter_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_asset(ter=-0.001)


class TestUniverse:
    @pytest.fixture
    def sample_universe(self) -> Universe:
        return Universe(
            [
                make_asset(
                    ticker="IWDA.AS",
                    isin="IE00B4L5Y983",
                    asset_class=AssetClass.EQUITY_DM,
                    region=Region.GLOBAL,
                ),
                make_asset(
                    ticker="EIMI.L",
                    isin="IE00BKM4GZ66",
                    name="iShares EM IMI",
                    asset_class=AssetClass.EQUITY_EM,
                    region=Region.EMERGING,
                ),
                make_asset(
                    ticker="IGLN.L",
                    isin="IE00B4ND3602",
                    name="iShares Physical Gold",
                    asset_class=AssetClass.GOLD,
                    region=Region.GLOBAL,
                    currency="USD",
                    ter=0.0012,
                ),
            ]
        )

    def test_length(self, sample_universe: Universe) -> None:
        assert len(sample_universe) == 3

    def test_contains_isin(self, sample_universe: Universe) -> None:
        assert "IE00B4L5Y983" in sample_universe

    def test_get_by_isin(self, sample_universe: Universe) -> None:
        a = sample_universe.get("IE00B4ND3602")
        assert a.ticker == "IGLN.L"

    def test_by_class_returns_subset(self, sample_universe: Universe) -> None:
        gold_only = sample_universe.by_class(AssetClass.GOLD)
        assert len(gold_only) == 1
        assert gold_only.assets[0].ticker == "IGLN.L"

    def test_chained_filters(self, sample_universe: Universe) -> None:
        eq_global = sample_universe.by_class(AssetClass.EQUITY_DM).by_region(Region.GLOBAL)
        assert len(eq_global) == 1

    def test_predicate_filter(self, sample_universe: Universe) -> None:
        cheap = sample_universe.filter(lambda a: a.ter < 0.0015)
        assert len(cheap) == 1
        assert cheap.assets[0].ticker == "IGLN.L"

    def test_duplicate_isin_raises(self) -> None:
        a1 = make_asset()
        a2 = make_asset(ticker="OTHER")  # same ISIN
        with pytest.raises(ValueError, match="Duplicate ISIN"):
            Universe([a1, a2])
