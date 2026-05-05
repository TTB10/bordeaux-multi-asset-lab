"""Quick diagnostic for a single Yahoo Finance ticker.

Usage:
    uv run python scripts/check_ticker.py NDIA.L
"""

from __future__ import annotations

import sys

import yfinance as yf


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_ticker.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1]
    df = yf.Ticker(ticker).history(period="3y")

    print()
    print("=" * 60)
    print(f"  {ticker}")
    print("=" * 60)

    if df.empty:
        print("  No data returned. Ticker likely delisted or not on Yahoo.")
        return

    close = df["Close"]
    total_ret = (close.iloc[-1] / close.iloc[0] - 1) * 100
    daily_ret = close.pct_change().dropna()
    ann_vol = daily_ret.std() * (252**0.5) * 100

    print(f"  Rows         : {len(df)}")
    print(f"  Period       : {df.index[0].date()} -> {df.index[-1].date()}")
    print(f"  First Close  : {close.iloc[0]:.2f}")
    print(f"  Last Close   : {close.iloc[-1]:.2f}")
    print(f"  Min Close    : {close.min():.2f}")
    print(f"  Max Close    : {close.max():.2f}")
    print(f"  Total return : {total_ret:+.1f}%")
    print(f"  Ann vol      : {ann_vol:.1f}%")
    print()
    print("  First 5 rows:")
    print(df[["Open", "Close"]].head(5).round(2).to_string())
    print()
    print("  Last 5 rows:")
    print(df[["Open", "Close"]].tail(5).round(2).to_string())
    print()


if __name__ == "__main__":
    main()
