"""End-to-end demo: fetch yield curve from FRED and produce an IndicatorReading.

Run from repo root:
    uv run python scripts/demo_yield_curve.py
"""

from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from bml.data.providers import FREDProvider
from bml.regime.indicators import YieldCurveIndicator


def main() -> None:
    load_dotenv()

    provider = FREDProvider()
    indicator = YieldCurveIndicator(provider)
    reading = indicator.read(as_of=date.today())

    print()
    print("=" * 70)
    print(f"  YIELD CURVE INDICATOR — as of {reading.as_of}")
    print("=" * 70)
    print(f"  Indicator    : {reading.indicator_name}")
    print(f"  Dimension    : {reading.dimension.value}")
    print(f"  Current value: {reading.value:+.2f}%")
    print(f"  Z-score (5y) : {reading.z_score}")
    print(f"  Direction    : {reading.direction.value.upper()}")
    print(f"  Confidence   : {reading.confidence:.0%}")
    print("=" * 70)
    print()

    if reading.direction.value == "down":
        print("Interpretation: yield curve signals DECELERATION / RECESSION risk.")
    elif reading.direction.value == "up":
        print("Interpretation: yield curve signals EXPANSION (steepening trend).")
    else:
        print("Interpretation: yield curve in NEUTRAL zone, no clear signal.")


if __name__ == "__main__":
    main()
