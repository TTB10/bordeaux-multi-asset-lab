"""Demo: load the shipped universe and compute performance stats by asset class.

Run from the repo root:
    uv run python scripts/demo_universe.py
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from loguru import logger

from bml.data import PriceLoader
from bml.data.providers import YFinanceProvider
from bml.universe import UniverseLoader


def _summary_stats(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple performance stats over the available history."""
    daily = prices.pct_change().dropna()
    n_obs = len(prices)
    total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
    ann_return = ((prices.iloc[-1] / prices.iloc[0]) ** (252 / n_obs) - 1) * 100
    ann_vol = daily.std() * (252**0.5) * 100
    sharpe = ann_return / ann_vol.replace(0, pd.NA)

    cum = (1 + daily).cumprod()
    drawdown = (cum / cum.cummax() - 1) * 100
    max_dd = drawdown.min()

    return pd.DataFrame(
        {
            "TotalRet%": total_return.round(1),
            "AnnRet%": ann_return.round(1),
            "Vol%": ann_vol.round(1),
            "Sharpe": sharpe.round(2),
            "MaxDD%": max_dd.round(1),
        }
    )


def main() -> None:
    universe = UniverseLoader.load()
    logger.info("Universe loaded: {n} assets", n=len(universe))

    end = date.today()
    start = end - timedelta(days=365 * 3)

    loader = PriceLoader(YFinanceProvider())
    result = loader.fetch_universe(universe, start, end)

    print()
    print("=" * 78)
    print(f"  PRICE FETCH SUMMARY  ({start} -> {end})")
    print("=" * 78)
    print(f"  Universe size : {len(universe)}")
    print(f"  Successful    : {len(result.successful)}")
    print(f"  Failed        : {len(result.failed)}")
    if result.failed:
        print()
        print("  Failed tickers (need manual review):")
        for t, reason in sorted(result.failed.items()):
            asset = universe.get(next(a.isin for a in universe if a.ticker == t))
            print(f"    {t:<10} [{asset.asset_class:<28}] -> {reason}")
    print("=" * 78)

    if result.prices.empty:
        logger.error("No usable price data, aborting stats computation.")
        return

    stats = _summary_stats(result.prices)

    # Attach asset_class to allow grouping
    isin_by_ticker = {a.ticker: a for a in universe if a.ticker in result.successful}
    stats["Class"] = stats.index.map(lambda t: isin_by_ticker[t].asset_class.value)
    stats["Region"] = stats.index.map(lambda t: isin_by_ticker[t].region.value)

    print()
    print("PERFORMANCE BY ASSET CLASS (median across funds)")
    print("-" * 78)
    by_class = (
        stats.groupby("Class")[["TotalRet%", "AnnRet%", "Vol%", "Sharpe", "MaxDD%"]]
        .median()
        .round(1)
        .sort_values("AnnRet%", ascending=False)
    )
    print(by_class.to_string())

    print()
    print("TOP 10 BY SHARPE RATIO")
    print("-" * 78)
    top = stats.sort_values("Sharpe", ascending=False).head(10)
    print(top.to_string())

    print()
    print("BOTTOM 5 BY SHARPE RATIO")
    print("-" * 78)
    bottom = stats.sort_values("Sharpe", ascending=True).head(5)
    print(bottom.to_string())


if __name__ == "__main__":
    main()
