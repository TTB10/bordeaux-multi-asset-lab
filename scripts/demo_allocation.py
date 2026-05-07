"""End-to-end demo: detect regime, then derive a TargetAllocation.

Run from repo root:
    uv run python scripts/demo_allocation.py
"""

from __future__ import annotations

from datetime import date

from dotenv import load_dotenv

from bml.allocation import RegimeBasedTacticalStrategy
from bml.allocation.tilts import NEUTRAL_TILT
from bml.data.providers import FREDProvider
from bml.regime import RuleBasedRegimeDetector
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)


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
    strategy = RegimeBasedTacticalStrategy()

    today = date.today()
    signal = detector.detect(as_of=today)
    allocation = strategy.compute(signal)

    print()
    print("=" * 78)
    print(f"  TARGET ALLOCATION — as of {today}")
    print("=" * 78)
    print(f"  Detected regime  : {signal.regime.value.upper()}")
    print(f"  Regime confidence: {signal.confidence:.0%}")
    print("  Smoothing rule   : confidence * regime_tilt + (1-confidence) * neutral")
    print()
    print(f"  {'Asset class':<32} {'Neutral':>9} {'Target':>9} {'Delta':>9}")
    print("  " + "-" * 60)

    target_dict = allocation.as_dict()
    all_classes = sorted(set(NEUTRAL_TILT) | set(target_dict), key=lambda x: x.value)
    for ac in all_classes:
        neutral_w = NEUTRAL_TILT.get(ac, 0.0)
        target_w = target_dict.get(ac, 0.0)
        delta = target_w - neutral_w
        sign = "+" if delta > 0 else ""
        print(f"  {ac.value:<32} {neutral_w:>8.1%} {target_w:>8.1%} {sign}{delta:>+8.1%}")
    print("  " + "-" * 60)
    total = sum(b.weight for b in allocation.buckets)
    print(f"  {'TOTAL':<32} {' ':>8} {total:>8.1%}")
    print("=" * 78)
    print()


if __name__ == "__main__":
    main()
