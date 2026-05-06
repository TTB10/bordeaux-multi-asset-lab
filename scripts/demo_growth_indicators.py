"""End-to-end demo: fetch all 3 growth indicators and display readings side by side.

Run from repo root:
    uv run python scripts/demo_growth_indicators.py
"""

from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from bml.data.providers import FREDProvider
from bml.regime.indicators import (
    IndustrialProductionIndicator,
    JoblessClaimsIndicator,
    MacroIndicator,
    YieldCurveIndicator,
)
from bml.regime.models import IndicatorReading


def _format_reading(r: IndicatorReading) -> str:
    z = f"{r.z_score:+.2f}" if r.z_score is not None else "N/A"
    return (
        f"  {r.indicator_name:<32} "
        f"value={r.value:+8.2f} "
        f"z={z:>7} "
        f"dir={r.direction.value.upper():<7} "
        f"conf={r.confidence:.0%}"
    )


def main() -> None:
    load_dotenv()
    provider = FREDProvider()

    indicators: list[MacroIndicator] = [
        YieldCurveIndicator(provider),
        IndustrialProductionIndicator(provider),
        JoblessClaimsIndicator(provider),
    ]

    today = date.today()
    print()
    print("=" * 90)
    print(f"  GROWTH INDICATORS — as of {today}")
    print("=" * 90)
    readings: list[IndicatorReading] = []
    for ind in indicators:
        try:
            r = ind.read(today)
            readings.append(r)
            print(_format_reading(r))
        except Exception as exc:
            print(f"  {ind.name:<32} FAILED: {exc}")
    print("=" * 90)

    if not readings:
        return

    # Naive vote (we'll replace with proper aggregator in the next phase).
    votes = {
        "up": sum(1 for r in readings if r.direction.value == "up"),
        "down": sum(1 for r in readings if r.direction.value == "down"),
        "neutral": sum(1 for r in readings if r.direction.value == "neutral"),
    }
    print()
    print(f"Naive vote: UP={votes['up']}  DOWN={votes['down']}  NEUTRAL={votes['neutral']}")
    print()


if __name__ == "__main__":
    main()
