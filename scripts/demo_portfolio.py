"""End-to-end pipeline: detect regime, allocate, select funds, compute risk.

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
from bml.risk import (
    HistoricalRiskCalculator,
    portfolio_levels,
    portfolio_returns,
)
from bml.selection import TopNPerBucketStrategy
from bml.universe import UniverseLoader

BENCHMARK_60_40 = {"CSPX.L": 0.60, "IB01.L": 0.40}


def main() -> None:
    load_dotenv()
    today = date.today()
    print()
    print("=" * 92)
    print(f"  PORTFOLIO CONSTRUCTION — as of {today}")
    print("=" * 92)

    print("\n[1/6] Loading universe...")
    universe = UniverseLoader.load()
    print(f"      Loaded {len(universe)} assets.")

    print("[2/6] Fetching prices (3 years)...")
    end = today
    start = end - timedelta(days=365 * 3)
    price_loader = PriceLoader(YFinanceProvider())
    price_result = price_loader.fetch_universe(universe, start, end)
    print(f"      {len(price_result.successful)}/{len(universe)} tickers OK.")

    print("[3/6] Detecting macro regime...")
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

    print("[4/6] Computing target allocation...")
    target = RegimeBasedTacticalStrategy().compute(signal)

    print("[5/6] Selecting funds (top 2 per bucket, composite scoring)...")
    portfolio = TopNPerBucketStrategy(n_per_bucket=2).select(target, universe, price_result.prices)

    print("[6/6] Computing portfolio risk metrics...")
    weights = portfolio.as_dict()
    pf_returns = portfolio_returns(price_result.prices, weights)
    pf_levels = portfolio_levels(pf_returns, base=100.0)

    bench_returns = portfolio_returns(price_result.prices, BENCHMARK_60_40)
    bench_levels = portfolio_levels(bench_returns, base=100.0)

    risk_calc = HistoricalRiskCalculator()
    pf_metrics = risk_calc.compute(pf_levels, benchmark_prices=bench_levels, as_of=today)
    bench_metrics = risk_calc.compute(bench_levels, as_of=today)

    # Display portfolio
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
    print("  " + "-" * 88)
    print(f"  {'TOTAL':<10} {' ':<28} {sum(p.weight for p in portfolio.positions):>7.2%}")
    print("=" * 92)

    # Display risk metrics
    print()
    print("=" * 92)
    print("  RISK METRICS (3-year history, daily)")
    print("=" * 92)
    print(f"  {'Metric':<22} {'Portfolio':>14} {'Benchmark 60/40':>18}")
    print("  " + "-" * 56)
    rows = [
        (
            "Annual return",
            f"{pf_metrics.annual_return:+.2%}",
            f"{bench_metrics.annual_return:+.2%}",
        ),
        (
            "Annual volatility",
            f"{pf_metrics.annual_volatility:.2%}",
            f"{bench_metrics.annual_volatility:.2%}",
        ),
        ("Sharpe ratio", f"{pf_metrics.sharpe_ratio:+.2f}", f"{bench_metrics.sharpe_ratio:+.2f}"),
        ("Max drawdown", f"{pf_metrics.max_drawdown:+.2%}", f"{bench_metrics.max_drawdown:+.2%}"),
        ("VaR 95% (daily)", f"{pf_metrics.var_95:+.2%}", f"{bench_metrics.var_95:+.2%}"),
        ("CVaR 95% (daily)", f"{pf_metrics.cvar_95:+.2%}", f"{bench_metrics.cvar_95:+.2%}"),
        (
            "Beta vs 60/40",
            f"{pf_metrics.beta:+.2f}" if pf_metrics.beta is not None else "n/a",
            "1.00",
        ),
    ]
    for label, pf_val, bench_val in rows:
        print(f"  {label:<22} {pf_val:>14} {bench_val:>18}")
    print("=" * 92)

    if portfolio.notes:
        print()
        print("Notes:")
        for n in portfolio.notes:
            print(f"  - {n}")
    print()


if __name__ == "__main__":
    main()
