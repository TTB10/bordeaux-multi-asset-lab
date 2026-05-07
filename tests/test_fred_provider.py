"""Tests for FREDProvider retry-and-backoff behaviour."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pandas as pd
import pytest

from bml.data.providers.fred_provider import FREDProvider
from bml.data.providers.macro_base import MacroDataProviderError


def _make_provider(
    client: MagicMock,
    max_retries: int = 3,
    backoff_base: float = 0.0,
) -> FREDProvider:
    """Build a provider with no real backoff so tests are fast."""
    return FREDProvider(
        client=client,
        max_retries=max_retries,
        backoff_base_seconds=backoff_base,
    )


def _success_series() -> pd.Series:
    return pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
        name="X",
    )


class TestFREDProviderRetry:
    def test_first_call_succeeds_no_retry(self) -> None:
        client = MagicMock()
        client.get_series.return_value = _success_series()
        provider = _make_provider(client)

        result = provider.fetch_series("X", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 1
        assert len(result) == 3

    def test_retries_on_transient_value_error_then_succeeds(self) -> None:
        client = MagicMock()
        client.get_series.side_effect = [
            ValueError("Internal Server Error"),
            ValueError("Internal Server Error"),
            _success_series(),
        ]
        provider = _make_provider(client, max_retries=3)

        result = provider.fetch_series("X", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 3
        assert len(result) == 3

    def test_retries_on_5xx_http_error_then_succeeds(self) -> None:
        client = MagicMock()
        http_500 = HTTPError("https://fred", 500, "Internal Server Error", {}, None)  # type: ignore[arg-type]
        client.get_series.side_effect = [http_500, _success_series()]
        provider = _make_provider(client, max_retries=3)

        result = provider.fetch_series("X", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 2
        assert len(result) == 3

    def test_fails_after_max_retries(self) -> None:
        client = MagicMock()
        client.get_series.side_effect = ValueError("Internal Server Error")
        provider = _make_provider(client, max_retries=3)

        with pytest.raises(MacroDataProviderError, match="after 3 attempts"):
            provider.fetch_series("X", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 3

    def test_non_retryable_4xx_fails_immediately(self) -> None:
        client = MagicMock()
        http_404 = HTTPError("https://fred", 404, "Not Found", {}, None)  # type: ignore[arg-type]
        client.get_series.side_effect = http_404
        provider = _make_provider(client, max_retries=3)

        with pytest.raises(MacroDataProviderError, match="non-retryable"):
            provider.fetch_series("BAD_ID", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 1  # no retry

    def test_non_transient_value_error_fails_immediately(self) -> None:
        client = MagicMock()
        client.get_series.side_effect = ValueError("Bad Request: invalid series id")
        provider = _make_provider(client, max_retries=3)

        with pytest.raises(MacroDataProviderError):
            provider.fetch_series("BAD", date(2024, 1, 1), date(2024, 1, 3))

        assert client.get_series.call_count == 1

    def test_max_retries_validation(self) -> None:
        client = MagicMock()
        with pytest.raises(ValueError, match="max_retries"):
            FREDProvider(client=client, max_retries=0)

    def test_missing_api_key_raises(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="FRED_API_KEY"),
        ):
            FREDProvider()


class TestFREDProviderBackoff:
    def test_backoff_grows_exponentially(self) -> None:
        """Verify time.sleep is called with 1s, 2s, 4s for 3 failed attempts."""
        client = MagicMock()
        client.get_series.side_effect = [
            ValueError("Internal Server Error"),
            ValueError("Internal Server Error"),
            ValueError("Internal Server Error"),
        ]
        provider = FREDProvider(
            client=client,
            max_retries=3,
            backoff_base_seconds=1.0,
        )

        with (
            patch("bml.data.providers.fred_provider.time.sleep") as mock_sleep,
            pytest.raises(MacroDataProviderError),
        ):
            provider.fetch_series("X", date(2024, 1, 1), date(2024, 1, 3))

        # 3 attempts -> 2 sleeps (after attempts 1 and 2; no sleep after the last)
        assert mock_sleep.call_count == 2
        wait_durations = [call.args[0] for call in mock_sleep.call_args_list]
        assert wait_durations == [1.0, 2.0]
