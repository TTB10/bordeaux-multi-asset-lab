"""Sanity check: can we fetch a FRED series via fredapi ?

Run from repo root:
    uv run python scripts/check_fred.py
"""

from __future__ import annotations

import os
from datetime import date, timedelta

from dotenv import load_dotenv
from fredapi import Fred


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        msg = "FRED_API_KEY is not set. Did you create the .env file ?"
        raise RuntimeError(msg)

    fred = Fred(api_key=api_key)

    end = date.today()
    start = end - timedelta(days=365 * 2)

    print("Fetching T10Y3M (10Y - 3M Treasury yield) from FRED...")
    print(f"Period: {start} -> {end}")
    print()

    series = fred.get_series("T10Y3M", observation_start=start, observation_end=end)
    print(f"Rows received: {len(series)}")
    print(f"Type: {type(series).__name__}")
    print()
    print("Last 5 observations:")
    print(series.tail(5))
    print()
    print(f"Latest value: {series.iloc[-1]:.2f}%")


if __name__ == "__main__":
    main()
