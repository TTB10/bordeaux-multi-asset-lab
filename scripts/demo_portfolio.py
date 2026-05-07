"""End-to-end pipeline: detect regime, allocate, select funds, build a Portfolio.

Run from repo root:
    uv run python scripts/demo_portfolio.py
"""

from __future__ import annotations

from datetime import date, timedelta

from dotenv import load_dotenv

from bml.allocation import RegimeBasedTacticalStrategy
from bml.data import PriceLoader
from bml.data.providers import FREDProvider, YFinanceProvider
from bml.regime import RuleBasedRegimeDetector
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)
from bml.selection import TopNPerBucketStrategy
from bml.universe import UniverseLoader


def main() -> None:
    load_dotenv()
    today = date.today()
    print()
    print("=" * 92)
    print(f"  PORTFOLIO CONSTRUCTION — as of {today}")
    print("=" * 92)

    # 1. Load universe
    print("\n[1/5] Loading universe...")
    universe = UniverseLoader.load()
    print(f"      Loaded {len(universe)} assets.")

    # 2. Fetch prices
    print("[2/5] Fetching prices (3 years)...")
    end = today
    start = end - timedelta(days=365 * 3)
    price_loader = PriceLoader(YFinanceProvider())
    price_result = price_loader.fetch_universe(universe, start, end)
    print(f"      {len(price_result.successful)}/{len(universe)} tickers OK.")

    # 3. Detect regime
    print("[3/5] Detecting macro regime...")
    fred = FREDProvider()
    detector = RuleBasedRegimeDetector(
        indicators=[
            YieldCurveIndicator(fred),
            IndustrialProductionIndicator(fred),
            JoblessClaimsIndicator(fred),
            InflationBreakevenIndicator(fred),
            CoreCPIIndicator(fred),
            OilMomentumIndicator(fred),
        ]
    )
    signal = detector.detect(as_of=today)
    print(f"      Regime: {signal.regime.value.upper()} (confidence {signal.confidence:.0%})")

    # 4. Compute target allocation
    print("[4/5] Computing target allocation...")
    allocation_strategy = RegimeBasedTacticalStrategy()
    target = allocation_strategy.compute(signal)

    # 5. Select funds
    print("[5/5] Selecting funds (top 2 per bucket, composite scoring)...")
    selection_strategy = TopNPerBucketStrategy(n_per_bucket=2)
    portfolio = selection_strategy.select(target, universe, price_result.prices)

    # Display
    print()
    print("=" * 92)
    print(f"  FINAL PORTFOLIO — {len(portfolio.positions)} positions")
    print("=" * 92)
    print(f"  {'Ticker':<10} {'Bucket':<28} {'Weight':>8} {'Score':>8}  {'Name'}")
    print("  " + "-" * 88)
    for pos in sorted(portfolio.positions, key=lambda p: (-p.weight, p.asset.ticker)):
        print(
            f"  {pos.asset.ticker:<10} {pos.bucket.value:<28} "
            f"{pos.weight:>7.2%} {pos.score:>+8.2f}  {pos.asset.name}"
        )
    total = sum(p.weight for p in portfolio.positions)
    print("  " + "-" * 88)
    print(f"  {'TOTAL':<10} {' ':<28} {total:>7.2%}")
    print("=" * 92)

    if portfolio.notes:
        print()
        print("Notes:")
        for n in portfolio.notes:
            print(f"  - {n}")

    print()


if __name__ == "__main__":
    main()
