"""Default regime-based tilt tables.

These weights are inspired by the Bridgewater All Weather framework and
risk-parity literature. They represent moderate tactical tilts around a
balanced 60/40-enriched neutral portfolio:

  - Each table sums to exactly 1.0
  - Movements vs neutral are kept within ~15% on any single bucket
  - The neutral allocation is the fallback when regime confidence is low
    or when the regime is UNCERTAIN

These tilts are configurable: the AllocationStrategy constructor accepts
custom tilt tables, so calibration can evolve without changing logic.
"""

from __future__ import annotations

from bml.regime.enums import Regime
from bml.universe.asset import AssetClass

NEUTRAL_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.40,
    AssetClass.EQUITY_EM: 0.10,
    AssetClass.GOVERNMENT_BOND: 0.20,
    AssetClass.CREDIT_IG: 0.10,
    AssetClass.CREDIT_HY: 0.05,
    AssetClass.GOLD: 0.05,
    AssetClass.COMMODITY: 0.00,
    AssetClass.REAL_ESTATE: 0.05,
    AssetClass.CASH: 0.05,
}

GOLDILOCKS_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.50,
    AssetClass.EQUITY_EM: 0.10,
    AssetClass.GOVERNMENT_BOND: 0.15,
    AssetClass.CREDIT_IG: 0.10,
    AssetClass.CREDIT_HY: 0.05,
    AssetClass.GOLD: 0.00,
    AssetClass.COMMODITY: 0.00,
    AssetClass.REAL_ESTATE: 0.05,
    AssetClass.CASH: 0.05,
}

REFLATION_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.35,
    AssetClass.EQUITY_EM: 0.10,
    AssetClass.GOVERNMENT_BOND: 0.10,
    AssetClass.CREDIT_IG: 0.05,
    AssetClass.CREDIT_HY: 0.05,
    AssetClass.GOLD: 0.10,
    AssetClass.COMMODITY: 0.10,
    AssetClass.REAL_ESTATE: 0.10,
    AssetClass.CASH: 0.05,
}

DISINFLATION_RECESSION_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.25,
    AssetClass.EQUITY_EM: 0.05,
    AssetClass.GOVERNMENT_BOND: 0.35,
    AssetClass.CREDIT_IG: 0.15,
    AssetClass.CREDIT_HY: 0.00,
    AssetClass.GOLD: 0.05,
    AssetClass.COMMODITY: 0.00,
    AssetClass.REAL_ESTATE: 0.00,
    AssetClass.CASH: 0.15,
}

STAGFLATION_TILT: dict[AssetClass, float] = {
    AssetClass.EQUITY_DM: 0.25,
    AssetClass.EQUITY_EM: 0.05,
    AssetClass.GOVERNMENT_BOND: 0.15,
    AssetClass.CREDIT_IG: 0.05,
    AssetClass.CREDIT_HY: 0.00,
    AssetClass.GOLD: 0.15,
    AssetClass.COMMODITY: 0.15,
    AssetClass.REAL_ESTATE: 0.05,
    AssetClass.CASH: 0.15,
}

DEFAULT_REGIME_TILTS: dict[Regime, dict[AssetClass, float]] = {
    Regime.GOLDILOCKS: GOLDILOCKS_TILT,
    Regime.REFLATION: REFLATION_TILT,
    Regime.DISINFLATION_RECESSION: DISINFLATION_RECESSION_TILT,
    Regime.STAGFLATION: STAGFLATION_TILT,
}
