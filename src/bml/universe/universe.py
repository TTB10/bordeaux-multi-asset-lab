"""Investable universe: a typed collection of assets with filtering helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Self

from bml.universe.asset import Asset, AssetClass, Region


class Universe:
    """A collection of investable assets, with composable filtering.

    The Universe is the canonical input to any allocation or selection logic.
    All filter operations return a new Universe (immutable-friendly), so
    expressions can be chained without side effects:

        eq_us = universe.by_class(AssetClass.EQUITY_DM).by_region(Region.USA)
    """

    def __init__(self, assets: list[Asset]) -> None:
        self._assets: list[Asset] = list(assets)
        self._by_isin: dict[str, Asset] = {a.isin: a for a in self._assets}
        if len(self._by_isin) != len(self._assets):
            raise ValueError("Duplicate ISIN detected in universe.")

    @property
    def assets(self) -> list[Asset]:
        return list(self._assets)

    def __len__(self) -> int:
        return len(self._assets)

    def __iter__(self) -> Iterator[Asset]:
        return iter(self._assets)

    def __contains__(self, isin: object) -> bool:
        return isin in self._by_isin

    def get(self, isin: str) -> Asset:
        """Retrieve an asset by ISIN. Raises KeyError if absent."""
        return self._by_isin[isin]

    def by_class(self, asset_class: AssetClass) -> Self:
        return type(self)([a for a in self._assets if a.asset_class == asset_class])

    def by_region(self, region: Region) -> Self:
        return type(self)([a for a in self._assets if a.region == region])

    def by_currency(self, currency: str) -> Self:
        currency = currency.upper()
        return type(self)([a for a in self._assets if a.currency == currency])

    def filter(self, predicate: Callable[[Asset], bool]) -> Self:
        """Filter by an arbitrary predicate function."""
        return type(self)([a for a in self._assets if predicate(a)])

    def tickers(self) -> list[str]:
        return [a.ticker for a in self._assets]

    def isins(self) -> list[str]:
        return [a.isin for a in self._assets]

    def __repr__(self) -> str:
        return f"Universe(n={len(self)})"
