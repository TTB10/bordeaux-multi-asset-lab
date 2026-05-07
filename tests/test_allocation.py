"""Unit tests for the allocation module."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from bml.allocation import (
    BucketWeight,
    RegimeBasedTacticalStrategy,
    TargetAllocation,
)
from bml.allocation.tilts import (
    DEFAULT_REGIME_TILTS,
    DISINFLATION_RECESSION_TILT,
    GOLDILOCKS_TILT,
    NEUTRAL_TILT,
    REFLATION_TILT,
    STAGFLATION_TILT,
)
from bml.regime.enums import Direction, MacroDimension, Regime
from bml.regime.models import DimensionalSignal, RegimeSignal
from bml.universe.asset import AssetClass


def _signal(regime: Regime, confidence: float) -> RegimeSignal:
    """Build a synthetic RegimeSignal for tests (without real readings)."""
    growth = DimensionalSignal(
        dimension=MacroDimension.GROWTH,
        as_of=date(2026, 5, 1),
        direction=Direction.UP
        if regime in (Regime.GOLDILOCKS, Regime.REFLATION)
        else Direction.DOWN,
        score=0.5,
        confidence=confidence,
        contributing_readings=[],
    )
    inflation = DimensionalSignal(
        dimension=MacroDimension.INFLATION,
        as_of=date(2026, 5, 1),
        direction=Direction.UP
        if regime in (Regime.REFLATION, Regime.STAGFLATION)
        else Direction.DOWN,
        score=0.5,
        confidence=confidence,
        contributing_readings=[],
    )
    if regime == Regime.UNCERTAIN:
        growth = growth.model_copy(update={"direction": Direction.NEUTRAL})
    return RegimeSignal(
        as_of=date(2026, 5, 1),
        regime=regime,
        growth_signal=growth,
        inflation_signal=inflation,
        confidence=confidence,
    )


class TestTiltTablesIntegrity:
    @pytest.mark.parametrize(
        ("name", "tilt"),
        [
            ("neutral", NEUTRAL_TILT),
            ("goldilocks", GOLDILOCKS_TILT),
            ("reflation", REFLATION_TILT),
            ("disinflation_recession", DISINFLATION_RECESSION_TILT),
            ("stagflation", STAGFLATION_TILT),
        ],
    )
    def test_each_tilt_sums_to_one(self, name: str, tilt: dict[AssetClass, float]) -> None:
        total = sum(tilt.values())
        assert abs(total - 1.0) < 1e-6, f"{name} sums to {total}"

    def test_default_tilts_cover_main_regimes(self) -> None:
        for r in (
            Regime.GOLDILOCKS,
            Regime.REFLATION,
            Regime.DISINFLATION_RECESSION,
            Regime.STAGFLATION,
        ):
            assert r in DEFAULT_REGIME_TILTS

    def test_uncertain_is_not_in_regime_tilts(self) -> None:
        # UNCERTAIN must fall back to neutral, not have its own tilt.
        assert Regime.UNCERTAIN not in DEFAULT_REGIME_TILTS


class TestTargetAllocationModel:
    def test_valid_allocation(self) -> None:
        ta = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.6),
                BucketWeight(asset_class=AssetClass.GOVERNMENT_BOND, weight=0.4),
            ],
        )
        assert ta.weight_of(AssetClass.EQUITY_DM) == pytest.approx(0.6)
        assert ta.weight_of(AssetClass.GOLD) == 0.0

    def test_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match=r"must sum to 1\.0"):
            TargetAllocation(
                as_of=date(2026, 5, 1),
                buckets=[
                    BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.6),
                    BucketWeight(asset_class=AssetClass.GOVERNMENT_BOND, weight=0.5),
                ],
            )

    def test_duplicate_asset_class_raises(self) -> None:
        with pytest.raises(ValidationError, match="Duplicate asset class"):
            TargetAllocation(
                as_of=date(2026, 5, 1),
                buckets=[
                    BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.5),
                    BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.5),
                ],
            )

    def test_as_dict_returns_full_mapping(self) -> None:
        ta = TargetAllocation(
            as_of=date(2026, 5, 1),
            buckets=[
                BucketWeight(asset_class=AssetClass.EQUITY_DM, weight=0.7),
                BucketWeight(asset_class=AssetClass.CASH, weight=0.3),
            ],
        )
        d = ta.as_dict()
        assert d == {AssetClass.EQUITY_DM: 0.7, AssetClass.CASH: 0.3}


class TestRegimeBasedTacticalStrategy:
    def test_full_confidence_returns_regime_tilt(self) -> None:
        strategy = RegimeBasedTacticalStrategy()
        signal = _signal(Regime.GOLDILOCKS, confidence=1.0)
        alloc = strategy.compute(signal)

        # At confidence 1.0, allocation should match GOLDILOCKS_TILT exactly
        for ac, expected_w in GOLDILOCKS_TILT.items():
            assert alloc.weight_of(ac) == pytest.approx(expected_w, abs=1e-4)

    def test_zero_confidence_returns_neutral(self) -> None:
        strategy = RegimeBasedTacticalStrategy()
        signal = _signal(Regime.STAGFLATION, confidence=0.0)
        alloc = strategy.compute(signal)

        for ac, expected_w in NEUTRAL_TILT.items():
            assert alloc.weight_of(ac) == pytest.approx(expected_w, abs=1e-4)

    def test_intermediate_confidence_interpolates(self) -> None:
        strategy = RegimeBasedTacticalStrategy()
        signal = _signal(Regime.REFLATION, confidence=0.5)
        alloc = strategy.compute(signal)

        # Equity DM: neutral 0.40, reflation 0.35 -> at conf 0.5 -> 0.375
        assert alloc.weight_of(AssetClass.EQUITY_DM) == pytest.approx(0.375, abs=1e-4)
        # Commodity: neutral 0.00, reflation 0.10 -> at conf 0.5 -> 0.05
        assert alloc.weight_of(AssetClass.COMMODITY) == pytest.approx(0.05, abs=1e-4)

    def test_uncertain_returns_neutral_regardless_of_confidence(self) -> None:
        strategy = RegimeBasedTacticalStrategy()
        signal = _signal(Regime.UNCERTAIN, confidence=0.9)
        alloc = strategy.compute(signal)

        for ac, expected_w in NEUTRAL_TILT.items():
            assert alloc.weight_of(ac) == pytest.approx(expected_w, abs=1e-4)
        assert alloc.regime_label == "uncertain"

    def test_output_weights_sum_to_one(self) -> None:
        strategy = RegimeBasedTacticalStrategy()
        for regime in (
            Regime.GOLDILOCKS,
            Regime.REFLATION,
            Regime.DISINFLATION_RECESSION,
            Regime.STAGFLATION,
            Regime.UNCERTAIN,
        ):
            for conf in (0.0, 0.3, 0.6, 0.9, 1.0):
                alloc = strategy.compute(_signal(regime, confidence=conf))
                total = sum(b.weight for b in alloc.buckets)
                assert abs(total - 1.0) < 1e-6, f"{regime}@{conf}: {total}"

    def test_rejects_invalid_neutral_tilt(self) -> None:
        bad = {AssetClass.EQUITY_DM: 0.6, AssetClass.CASH: 0.5}
        with pytest.raises(ValueError, match="Neutral tilt"):
            RegimeBasedTacticalStrategy(neutral_tilt=bad)

    def test_rejects_invalid_regime_tilt(self) -> None:
        bad_tilts = {Regime.GOLDILOCKS: {AssetClass.EQUITY_DM: 0.7, AssetClass.CASH: 0.5}}
        with pytest.raises(ValueError, match="Tilt for"):
            RegimeBasedTacticalStrategy(regime_tilts=bad_tilts)

    def test_low_confidence_stays_close_to_neutral(self) -> None:
        """At confidence 0.1, the allocation should move at most 10% from neutral on any bucket."""
        strategy = RegimeBasedTacticalStrategy()
        signal = _signal(Regime.STAGFLATION, confidence=0.1)
        alloc = strategy.compute(signal)
        for ac, neutral_w in NEUTRAL_TILT.items():
            actual_w = alloc.weight_of(ac)
            assert abs(actual_w - neutral_w) <= 0.05, (
                f"{ac}: |{actual_w} - {neutral_w}| should be <= 0.05 at 10% confidence"
            )
