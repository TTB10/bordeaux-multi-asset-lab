"""End-to-end regime detection on live FRED data.

Builds a RuleBasedRegimeDetector with 6 indicators, runs it against
today's date, and prints a structured regime signal with allocation hints.

Run from repo root:
    uv run python scripts/demo_all_indicators.py
"""

from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from bml.data.providers import FREDProvider
from bml.regime import Regime, RuleBasedRegimeDetector
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)
from bml.regime.models import DimensionalSignal, RegimeSignal


def _format_dimensional_signal(label: str, sig: DimensionalSignal) -> None:
    print(
        f"\n{label.upper()} DIMENSION  (direction = {sig.direction.value.upper()}, score = {sig.score:+.2f}, conf = {sig.confidence:.0%})"
    )
    print("-" * 92)
    for r in sig.contributing_readings:
        z = f"{r.z_score:+.2f}" if r.z_score is not None else "  N/A"
        print(
            f"  {r.indicator_name:<32} value={r.value:+10.2f}  z={z:>6}  "
            f"dir={r.direction.value.upper():<7}  conf={r.confidence:.0%}"
        )


def _format_regime(signal: RegimeSignal) -> None:
    print()
    print("=" * 92)
    print(
        f"  REGIME : {signal.regime.value.upper():<25} (overall confidence = {signal.confidence:.0%})"
    )
    print("=" * 92)


_TILTS = {
    Regime.GOLDILOCKS: "OVERWEIGHT equities, IG credit, REITs.",
    Regime.REFLATION: "OVERWEIGHT commodities, value equities, real estate.",
    Regime.DISINFLATION_RECESSION: "OVERWEIGHT long-duration sovereigns, cash. AVOID equities.",
    Regime.STAGFLATION: "OVERWEIGHT gold, broad commodities, TIPS.",
    Regime.UNCERTAIN: "Maintain neutral allocation until signal strengthens.",
}


def main() -> None:
    load_dotenv()
    provider = FREDProvider()

    detector = RuleBasedRegimeDetector(
        indicators=[
            YieldCurveIndicator(provider),
            IndustrialProductionIndicator(provider),
            JoblessClaimsIndicator(provider),
            InflationBreakevenIndicator(provider),
            CoreCPIIndicator(provider),
            OilMomentumIndicator(provider),
        ]
    )

    today = date.today()
    signal = detector.detect(as_of=today)

    print()
    print("=" * 92)
    print(f"  MACRO REGIME — as of {today}")
    print("=" * 92)
    _format_dimensional_signal("Growth", signal.growth_signal)
    _format_dimensional_signal("Inflation", signal.inflation_signal)
    _format_regime(signal)
    print(f"Allocation tilts: {_TILTS[signal.regime]}\n")


if __name__ == "__main__":
    main()
