"""Macro indicators feeding the regime detection pipeline."""

from bml.regime.indicators.base import MacroIndicator
from bml.regime.indicators.core_cpi import CoreCPIIndicator
from bml.regime.indicators.industrial_production import IndustrialProductionIndicator
from bml.regime.indicators.inflation_breakeven import InflationBreakevenIndicator
from bml.regime.indicators.jobless_claims import JoblessClaimsIndicator
from bml.regime.indicators.oil_momentum import OilMomentumIndicator
from bml.regime.indicators.yield_curve import YieldCurveIndicator

__all__ = [
    "CoreCPIIndicator",
    "IndustrialProductionIndicator",
    "InflationBreakevenIndicator",
    "JoblessClaimsIndicator",
    "MacroIndicator",
    "OilMomentumIndicator",
    "YieldCurveIndicator",
]
