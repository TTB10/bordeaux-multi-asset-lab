"""End-to-end demo: 6 indicators -> 2x2 regime classification.

Uses a simple majority vote within each dimension to derive growth and
inflation directions, then maps the pair to one of 5 regimes.

Run from repo root:
    uv run python scripts/demo_all_indicators.py
"""

from __future__ import annotations

from collections import Counter
from datetime import date

from dotenv import load_dotenv

from bml.data.providers import FREDProvider
from bml.regime.enums import Direction, MacroDimension, Regime
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    MacroIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)
from bml.regime.models import IndicatorReading


def _format_reading(r: IndicatorReading) -> str:
    z = f"{r.z_score:+.2f}" if r.z_score is not None else "  N/A"
    return (
        f"  {r.indicator_name:<32} "
        f"value={r.value:+10.2f} "
        f"z={z:>6} "
        f"dir={r.direction.value.upper():<7} "
        f"conf={r.confidence:.0%}"
    )


def _majority_direction(readings: list[IndicatorReading]) -> Direction:
    """Simple majority vote ignoring NEUTRAL ties."""
    counts = Counter(r.direction for r in readings)
    up = counts.get(Direction.UP, 0)
    down = counts.get(Direction.DOWN, 0)
    if up > down:
        return Direction.UP
    if down > up:
        return Direction.DOWN
    return Direction.NEUTRAL


def main() -> None:
    load_dotenv()
    provider = FREDProvider()

    indicators: list[MacroIndicator] = [
        YieldCurveIndicator(provider),
        IndustrialProductionIndicator(provider),
        JoblessClaimsIndicator(provider),
        InflationBreakevenIndicator(provider),
        CoreCPIIndicator(provider),
        OilMomentumIndicator(provider),
    ]

    today = date.today()

    growth_readings: list[IndicatorReading] = []
    inflation_readings: list[IndicatorReading] = []

    print()
    print("=" * 92)
    print(f"  MACRO REGIME — as of {today}")
    print("=" * 92)

    print()
    print("GROWTH DIMENSION")
    print("-" * 92)
    for ind in indicators:
        if ind.dimension == MacroDimension.GROWTH:
            try:
                r = ind.read(today)
                growth_readings.append(r)
                print(_format_reading(r))
            except Exception as exc:
                print(f"  {ind.name:<32} FAILED: {exc}")

    print()
    print("INFLATION DIMENSION")
    print("-" * 92)
    for ind in indicators:
        if ind.dimension == MacroDimension.INFLATION:
            try:
                r = ind.read(today)
                inflation_readings.append(r)
                print(_format_reading(r))
            except Exception as exc:
                print(f"  {ind.name:<32} FAILED: {exc}")

    print()
    print("=" * 92)
    growth_dir = _majority_direction(growth_readings) if growth_readings else Direction.NEUTRAL
    inflation_dir = (
        _majority_direction(inflation_readings) if inflation_readings else Direction.NEUTRAL
    )
    regime = Regime.from_directions(growth_dir, inflation_dir)

    print(f"  Growth direction    : {growth_dir.value.upper()}")
    print(f"  Inflation direction : {inflation_dir.value.upper()}")
    print(f"  -> REGIME           : {regime.value.upper()}")
    print("=" * 92)
    print()

    if regime == Regime.GOLDILOCKS:
        print("Asset class tilts (typical): OVERWEIGHT equities, IG credit, REITs.")
    elif regime == Regime.REFLATION:
        print("Asset class tilts (typical): OVERWEIGHT commodities, value equities, real estate.")
    elif regime == Regime.DISINFLATION_RECESSION:
        print(
            "Asset class tilts (typical): OVERWEIGHT long-duration sovereigns, cash. AVOID equities."
        )
    elif regime == Regime.STAGFLATION:
        print("Asset class tilts (typical): OVERWEIGHT gold, broad commodities, TIPS.")
    else:
        print("Regime unclear; maintain neutral allocation until signal strengthens.")
    print()


if __name__ == "__main__":
    main()
