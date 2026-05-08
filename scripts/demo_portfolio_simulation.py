"""End-to-end demo: initialize a portfolio with capital, save, reload, verify.

Run from repo root:
    uv run python scripts/demo_portfolio_simulation.py
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from bml.allocation import RegimeBasedTacticalStrategy
from bml.data import PriceLoader
from bml.data.providers import FREDProvider, YFinanceProvider
from bml.portfolio import PortfolioSimulator
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

INITIAL_CAPITAL = 100_000.0  # 100k EUR
PORTFOLIO_FILE = Path("data/portfolios/portfolio_latest.json")


def main() -> None:
    load_dotenv()
    today = date.today()

    print()
    print("=" * 92)
    print(f"  PORTFOLIO INITIALIZATION — {today}")
    print(f"  Initial capital: {INITIAL_CAPITAL:,.0f} EUR")
    print("=" * 92)

    # 1. Build target portfolio (regime + allocation + selection)
    print("\n[1/4] Building target portfolio (regime -> allocation -> selection)...")
    universe = UniverseLoader.load()
    end = today
    start = end - timedelta(days=365 * 3)
    price_loader = PriceLoader(YFinanceProvider())
    price_result = price_loader.fetch_universe(universe, start, end)

    detector = RuleBasedRegimeDetector(
        indicators=[
            YieldCurveIndicator(FREDProvider()),
            IndustrialProductionIndicator(FREDProvider()),
            JoblessClaimsIndicator(FREDProvider()),
            InflationBreakevenIndicator(FREDProvider()),
            CoreCPIIndicator(FREDProvider()),
            OilMomentumIndicator(FREDProvider()),
        ]
    )
    signal = detector.detect(as_of=today)
    target_alloc = RegimeBasedTacticalStrategy().compute(signal)
    portfolio = TopNPerBucketStrategy(n_per_bucket=2).select(
        target_alloc, universe, price_result.prices
    )
    print(f"      Regime: {signal.regime.value.upper()} (conf {signal.confidence:.0%})")
    print(f"      Target portfolio: {len(portfolio.positions)} positions")

    # 2. Initialize portfolio state
    print(f"\n[2/4] Initializing portfolio with {INITIAL_CAPITAL:,.0f} EUR...")
    state = PortfolioSimulator.initialize(
        target=portfolio,
        prices=price_result.prices,
        capital=INITIAL_CAPITAL,
        as_of=today,
    )
    print(f"      Created {len(state.positions)} positions")
    print(f"      Total value: {state.total_value:,.2f} EUR")
    print(f"      Cash residual: {state.cash:,.2f} EUR")

    # 3. Persist to disk
    print(f"\n[3/4] Saving state to {PORTFOLIO_FILE}...")
    PortfolioSimulator.save(state, PORTFOLIO_FILE)
    file_size_kb = PORTFOLIO_FILE.stat().st_size / 1024
    print(f"      Saved {file_size_kb:.1f} KB")

    # 4. Reload and verify integrity
    print("\n[4/4] Reloading state and verifying integrity...")
    loaded = PortfolioSimulator.load(PORTFOLIO_FILE)
    assert loaded.total_value == state.total_value
    assert len(loaded.positions) == len(state.positions)
    assert loaded.transactions == state.transactions
    print("      Integrity check passed ✓")

    # Display detailed positions
    print()
    print("=" * 92)
    print(f"  PORTFOLIO POSITIONS ({len(state.positions)} holdings)")
    print("=" * 92)
    print(f"  {'Ticker':<10} {'Bucket':<28} {'Qty':>10} {'Price':>10} {'Value':>14}")
    print("  " + "-" * 80)
    for pos in sorted(state.positions, key=lambda p: -p.market_value):
        print(
            f"  {pos.asset.ticker:<10} {pos.bucket.value:<28} "
            f"{pos.quantity:>10.4f} {pos.current_price:>10.2f} "
            f"{pos.market_value:>13,.2f}"
        )
    print("  " + "-" * 80)
    print(f"  {'TOTAL POSITIONS':<48} {state.invested_value:>13,.2f}")
    print(f"  {'CASH':<48} {state.cash:>13,.2f}")
    print(f"  {'TOTAL VALUE':<48} {state.total_value:>13,.2f}")
    print("=" * 92)
    print()
    print(f"NAV per share (base 100 at inception): {state.nav_per_share:.4f}")
    print(f"Total return since inception: {state.total_return:+.2%}")
    print()
    print("Next workflow: re-run this script in 1 month to rebalance and track perf.")
    print()


if __name__ == "__main__":
    main()
