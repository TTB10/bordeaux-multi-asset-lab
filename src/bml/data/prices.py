"""Price loading utilities: fetch prices for a Universe with robust error handling."""

from __future__ import annotations

from datetime import date
from typing import NamedTuple

import pandas as pd
from loguru import logger

from bml.data.providers import DataProvider, DataProviderError
from bml.universe import Universe


class PriceFetchResult(NamedTuple):
    """Outcome of a multi-asset price fetch.

    Attributes:
        prices: Wide DataFrame, columns are tickers, index is DatetimeIndex.
                Forward-filled and trimmed of leading NaN rows.
        successful: Tickers that were successfully fetched.
        failed: Tickers that returned no data, plus the reason.
    """

    prices: pd.DataFrame
    successful: list[str]
    failed: dict[str, str]


class PriceLoader:
    """Orchestrate price downloads for a Universe via a DataProvider.

    Tickers that fail are logged and reported but do not abort the run.
    Useful when working with hundreds of UCITS ETFs whose Yahoo coverage
    is uneven.
    """

    def __init__(self, provider: DataProvider) -> None:
        self._provider = provider

    def fetch_universe(
        self,
        universe: Universe,
        start: date,
        end: date,
    ) -> PriceFetchResult:
        """Fetch prices for every asset in the universe.

        Failed tickers are silently dropped from the output frame; their
        identifiers are returned in the `failed` map for inspection.
        """
        tickers = universe.tickers()
        logger.info("Fetching {n} tickers from provider", n=len(tickers))

        try:
            raw = self._provider.fetch_prices(tickers, start, end)
        except DataProviderError:
            logger.error("Bulk fetch failed; falling back to per-ticker fetch")
            return self._fetch_one_by_one(tickers, start, end)

        successful, failed = self._split_results(raw, tickers)
        clean = self._clean(raw[successful]) if successful else pd.DataFrame()

        logger.info(
            "Fetch complete: {ok}/{total} successful, {bad} failed",
            ok=len(successful),
            total=len(tickers),
            bad=len(failed),
        )
        return PriceFetchResult(prices=clean, successful=successful, failed=failed)

    def _fetch_one_by_one(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> PriceFetchResult:
        """Fallback path used when bulk fetch raises."""
        successful: list[str] = []
        failed: dict[str, str] = {}
        frames: list[pd.DataFrame] = []

        for t in tickers:
            try:
                df = self._provider.fetch_prices([t], start, end)
                if df.empty or df[t].dropna().empty:
                    failed[t] = "empty response"
                    continue
                frames.append(df)
                successful.append(t)
            except (DataProviderError, KeyError) as exc:
                failed[t] = str(exc)

        if not frames:
            return PriceFetchResult(pd.DataFrame(), [], failed)

        merged = pd.concat(frames, axis=1).sort_index()
        return PriceFetchResult(self._clean(merged), successful, failed)

    @staticmethod
    def _split_results(
        raw: pd.DataFrame,
        tickers: list[str],
    ) -> tuple[list[str], dict[str, str]]:
        """Identify which columns came back populated vs empty."""
        successful: list[str] = []
        failed: dict[str, str] = {}
        for t in tickers:
            if t not in raw.columns:
                failed[t] = "missing column"
            elif raw[t].dropna().empty:
                failed[t] = "all NaN"
            else:
                successful.append(t)
        return successful, failed

    @staticmethod
    def _clean(prices: pd.DataFrame) -> pd.DataFrame:
        """Forward-fill cross-calendar gaps and drop leading NaN rows."""
        return prices.ffill().dropna(how="any")
