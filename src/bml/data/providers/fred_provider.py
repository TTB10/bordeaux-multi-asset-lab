"""FRED (Federal Reserve Economic Data) implementation of MacroDataProvider."""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
from fredapi import Fred
from loguru import logger

from bml.data.providers.macro_base import MacroDataProvider, MacroDataProviderError


class FREDProvider(MacroDataProvider):
    """Fetch FRED time series via the official `fredapi` client.

    Requires a FRED API key. The key is read from the `FRED_API_KEY`
    environment variable (typically loaded from a `.env` file via
    python-dotenv).
    """

    def __init__(self, api_key: str | None = None) -> None:
        """
        Args:
            api_key: Override the API key. If None (default), read from
                the FRED_API_KEY environment variable.
        """
        key = api_key or os.environ.get("FRED_API_KEY")
        if not key:
            msg = (
                "FRED API key not provided. Set FRED_API_KEY in the "
                "environment or pass api_key= explicitly."
            )
            raise MacroDataProviderError(msg)
        self._client = Fred(api_key=key)

    def fetch_series(
        self,
        series_id: str,
        start: date,
        end: date,
    ) -> pd.Series:
        if not series_id:
            raise ValueError("series_id must not be empty")
        if start >= end:
            raise ValueError("start must be strictly before end")

        logger.info(
            "Fetching FRED series {sid} from {start} to {end}",
            sid=series_id,
            start=start,
            end=end,
        )

        try:
            series = self._client.get_series(
                series_id,
                observation_start=start,
                observation_end=end,
            )
        except Exception as exc:
            msg = f"FRED request failed for {series_id}: {exc}"
            raise MacroDataProviderError(msg) from exc

        if series is None or len(series) == 0:
            msg = f"FRED returned an empty series for {series_id}"
            raise MacroDataProviderError(msg)

        series.index = pd.to_datetime(series.index)
        series.name = series_id
        return series.sort_index()
