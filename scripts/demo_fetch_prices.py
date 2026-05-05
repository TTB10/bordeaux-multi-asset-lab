"""Demo script: fetch real prices for a small ETF universe via Yahoo Finance.

Run from the repo root:
    uv run python scripts/demo_fetch_prices.py
"""

from __future__ import annotations

from datetime import date, timedelta

from loguru import logger

from bml.data.providers import YFinanceProvider
from bml.universe import Asset, AssetClass, Region, Universe


def build_demo_universe() -> Universe:
    """Build a tiny multi-asset universe (5 UCITS ETFs)."""
    return Universe(
        [
            Asset(
                ticker="IWDA.AS",
                isin="IE00B4L5Y983",
                name="iShares Core MSCI World",
                asset_class=AssetClass.EQUITY_DM,
                region=Region.GLOBAL,
                currency="USD",
                ter=0.0020,
            ),
            Asset(
                ticker="EIMI.L",
                isin="IE00BKM4GZ66",
                name="iShares Core MSCI EM IMI",
                asset_class=AssetClass.EQUITY_EM,
                region=Region.EMERGING,
                currency="USD",
                ter=0.0018,
            ),
            Asset(
                ticker="IGLN.L",
                isin="IE00B4ND3602",
                name="iShares Physical Gold",
                asset_class=AssetClass.GOLD,
                region=Region.GLOBAL,
                currency="USD",
                ter=0.0012,
            ),
            Asset(
                ticker="IBGL.AS",
                isin="IE00B1FZS913",
                name="iShares Euro Government Bond 15-30y",
                asset_class=AssetClass.GOVERNMENT_BOND,
                region=Region.EUROZONE,
                currency="EUR",
                ter=0.0020,
            ),
            Asset(
                ticker="IHYG.L",
                isin="IE00B66F4759",
                name="iShares Euro High Yield Corporate Bond",
                asset_class=AssetClass.CREDIT_HY,
                region=Region.EUROPE,
                currency="EUR",
                ter=0.0050,
            ),
        ]
    )


def main() -> None:
    universe = build_demo_universe()
    logger.info("Universe built: {n} assets", n=len(universe))

    end = date.today()
    start = end - timedelta(days=365 * 3)  # 3 years of history

    provider = YFinanceProvider()
    raw_prices = provider.fetch_prices(
        tickers=universe.tickers(),
        start=start,
        end=end,
    )

    # Forward-fill across non-aligned trading calendars (e.g. UK vs Amsterdam holidays)
    # then drop any leading rows that are still partly NaN.
    prices = raw_prices.ffill().dropna(how="any")

    print()
    print("=" * 70)
    print(f"  Fetched {len(raw_prices)} raw rows -> {len(prices)} clean rows")
    print(f"  {len(prices.columns)} tickers, {prices.index.min().date()} -> {prices.index.max().date()}")
    print("=" * 70)
    print()
    print("Last 5 observations:")
    print(prices.tail().round(2))
    print()
    print("Total return over the period (%):")
    total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
    print(total_return.round(2).sort_values(ascending=False).to_string())
    print()
    print("Annualised volatility (%):")
    daily_returns = prices.pct_change().dropna()
    vol = daily_returns.std() * (252 ** 0.5) * 100
    print(vol.round(2).sort_values().to_string())
    print()
    print("Sharpe ratio (rf=0, period):")
    ann_return = ((prices.iloc[-1] / prices.iloc[0]) ** (252 / len(prices)) - 1) * 100
    sharpe = ann_return / vol
    print(sharpe.round(2).sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()