"""FRED data provider with retry-and-backoff for transient server errors.

The FRED API returns intermittent HTTP 5xx errors, especially on energy
and oil series during peak hours. This provider retries up to MAX_RETRIES
times with exponential backoff. Non-retryable errors (4xx, missing series,
authentication) fail fast with a clear message.
"""

from __future__ import annotations

import os
import time
from datetime import date
from typing import Any
from urllib.error import HTTPError

import pandas as pd
from fredapi import Fred
from loguru import logger

from bml.data.providers.macro_base import MacroDataProvider, MacroDataProviderError


class FREDProvider(MacroDataProvider):
    """FRED API client with automatic retry on transient errors."""

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_BASE_SECONDS = 1.0
    RETRYABLE_HTTP_CODES = (500, 502, 503, 504)
    TRANSIENT_KEYWORDS = (
        "internal server error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "timeout",
    )

    def __init__(
        self,
        api_key: str | None = None,
        client: Any | None = None,
        max_retries: int | None = None,
        backoff_base_seconds: float | None = None,
    ) -> None:
        """Construct the provider.

        Args:
            api_key: FRED API key. Falls back to env FRED_API_KEY.
            client: Optional pre-built fredapi.Fred (or compatible mock) for testing.
            max_retries: Number of attempts including the first call.
            backoff_base_seconds: Base of the exponential backoff (1s, 2s, 4s, ...).
        """
        if client is not None:
            self._client = client
        else:
            key = api_key or os.getenv("FRED_API_KEY")
            if not key:
                msg = "FRED_API_KEY not set (provide via constructor or .env)"
                raise ValueError(msg)
            self._client = Fred(api_key=key)

        self._max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        self._backoff_base = (
            backoff_base_seconds
            if backoff_base_seconds is not None
            else self.DEFAULT_BACKOFF_BASE_SECONDS
        )
        if self._max_retries < 1:
            msg = "max_retries must be >= 1"
            raise ValueError(msg)

    def fetch_series(self, series_id: str, start: date, end: date) -> pd.Series:
        logger.info(
            "Fetching FRED series {series_id} from {start} to {end}",
            series_id=series_id,
            start=start,
            end=end,
        )

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                result = self._client.get_series(
                    series_id,
                    observation_start=start,
                    observation_end=end,
                )
                return pd.Series(result)
            except HTTPError as exc:
                if exc.code not in self.RETRYABLE_HTTP_CODES:
                    msg = f"FRED request failed for {series_id}: HTTP {exc.code} (non-retryable)"
                    raise MacroDataProviderError(msg) from exc
                last_exc = exc
                self._sleep_if_more_attempts(series_id, attempt, exc)
            except ValueError as exc:
                # fredapi wraps urllib HTTPError in ValueError using the body message
                if not self._is_transient_value_error(exc):
                    msg = f"FRED request failed for {series_id}: {exc}"
                    raise MacroDataProviderError(msg) from exc
                last_exc = exc
                self._sleep_if_more_attempts(series_id, attempt, exc)

        msg = (
            f"FRED request failed for {series_id} after {self._max_retries} "
            f"attempts (last error: {last_exc})"
        )
        raise MacroDataProviderError(msg) from last_exc

    def _is_transient_value_error(self, exc: ValueError) -> bool:
        text = str(exc).lower()
        return any(kw in text for kw in self.TRANSIENT_KEYWORDS)

    def _sleep_if_more_attempts(
        self,
        series_id: str,
        attempt: int,
        exc: Exception,
    ) -> None:
        if attempt < self._max_retries:
            wait = self._backoff_base * (2 ** (attempt - 1))
            logger.warning(
                "FRED fetch for {series_id} failed (attempt {a}/{n}): {exc}. "
                "Retrying in {wait}s...",
                series_id=series_id,
                a=attempt,
                n=self._max_retries,
                exc=exc,
                wait=wait,
            )
            time.sleep(wait)
