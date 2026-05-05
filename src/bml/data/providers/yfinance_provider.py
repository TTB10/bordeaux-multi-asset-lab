"""Yahoo Finance implementation of the DataProvider interface."""

from __future__ import annotations

from datetime import date

import pandas as pd
import yfinance as yf
from loguru import logger

from bml.data.providers.base import DataProvider, DataProviderError


class YFinanceProvider(DataProvider):
    """Free Yahoo Finance data via the `yfinance` library.

    Notes:
        - Yahoo data is best-effort and not guaranteed for production use.
        - For UCITS ETFs, use the European listing ticker (e.g. "IWDA.AS").
    """

    def __init__(self, auto_adjust: bool = True) -> None:
        """
        Args:
            auto_adjust: If True (default), prices are adjusted for splits
                and dividends - the right choice for total-return analysis.
        """
        self._auto_adjust = auto_adjust

    def fetch_prices(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.DataFrame:
        if not tickers:
            raise ValueError("tickers must not be empty")
        if start >= end:
            raise ValueError("start must be strictly before end")

        logger.info(
            "Fetching {n} tickers from Yahoo Finance ({start} -> {end})",
            n=len(tickers),
            start=start,
            end=end,
        )

        try:
            raw = yf.download(
                tickers=tickers,
                start=start.isoformat(),
                end=end.isoformat(),
                auto_adjust=self._auto_adjust,
                progress=False,
                group_by="ticker",
                threads=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise DataProviderError(f"Yahoo Finance request failed: {exc}") from exc

        if raw is None or raw.empty:
            raise DataProviderError("Yahoo Finance returned an empty dataframe")

        prices = self._extract_close(raw, tickers)
        prices.index = pd.to_datetime(prices.index)
        prices = prices.sort_index()
        return prices

    @staticmethod
    def _extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
        """Normalise the multi-shape output of yfinance into a clean wide frame."""
        if len(tickers) == 1:
            ticker = tickers[0]
            if "Close" in raw.columns:
                return raw[["Close"]].rename(columns={"Close": ticker})
            raise DataProviderError(f"No Close column for {ticker}")

        # Multi-ticker: columns are a MultiIndex (ticker, field).
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw.xs("Close", axis=1, level=1)
            return close

        raise DataProviderError("Unexpected yfinance response shape")
