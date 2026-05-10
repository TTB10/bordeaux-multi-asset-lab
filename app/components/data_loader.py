"""Data loader with Streamlit caching for the full pipeline.

A single cached function runs the entire pipeline (universe load, price
fetch, regime detection, allocation, selection, risk metrics) and returns
a dataclass holding all the intermediate results. This keeps the Streamlit
pages fast on interactions while the underlying computation runs once
per hour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from bml.allocation import RegimeBasedTacticalStrategy
from bml.allocation.models import TargetAllocation
from bml.allocation.tilts import NEUTRAL_TILT
from bml.data import PriceLoader
from bml.data.providers import FREDProvider, YFinanceProvider
from bml.portfolio import PortfolioSimulator, PortfolioState
from bml.regime import RuleBasedRegimeDetector
from bml.regime.indicators import (
    CoreCPIIndicator,
    IndustrialProductionIndicator,
    InflationBreakevenIndicator,
    JoblessClaimsIndicator,
    OilMomentumIndicator,
    YieldCurveIndicator,
)
from bml.regime.models import RegimeSignal
from bml.risk import (
    HistoricalRiskCalculator,
    RiskMetrics,
    portfolio_levels,
    portfolio_returns,
)
from bml.selection import TopNPerBucketStrategy
from bml.selection.models import Portfolio
from bml.universe import Universe, UniverseLoader

BENCHMARK_60_40 = {"CSPX.L": 0.60, "IB01.L": 0.40}
INITIAL_CAPITAL = 100_000.0


@dataclass(frozen=True)
class PipelineState:
    """Container for the full pipeline output, returned by the cached loader."""

    today: date
    universe: Universe
    prices: pd.DataFrame
    n_successful: int
    n_failed: int
    regime_signal: RegimeSignal
    target_allocation: TargetAllocation
    portfolio: Portfolio
    portfolio_state: PortfolioState
    portfolio_metrics: RiskMetrics
    benchmark_metrics: RiskMetrics
    portfolio_levels_series: pd.Series
    benchmark_levels_series: pd.Series


def _resolve_fred_api_key() -> str:
    """Resolve FRED API key from either Streamlit secrets or .env file.

    Priority: Streamlit secrets (cloud) > environment variable / .env (local).
    """
    import os

    try:
        if "FRED_API_KEY" in st.secrets:
            return str(st.secrets["FRED_API_KEY"])
    except (FileNotFoundError, AttributeError):
        pass

    load_dotenv()
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY not found. Set it in .env (local) or Streamlit secrets (cloud)."
        )
    return key


@st.cache_data(ttl=3600, show_spinner="Téléchargement des données et exécution du pipeline...")
def load_pipeline_state() -> PipelineState:
    """Run the entire pipeline once per hour and return a packaged state.

    The cache key is implicit: with no parameter, Streamlit caches the result
    for the TTL window. Forcing a refresh requires using the "Clear cache"
    option in the Streamlit menu (top-right) or restarting the app.
    """
    today = date.today()
    fred_key = _resolve_fred_api_key()

    # 1. Universe + prices
    universe = UniverseLoader.load()
    end = today
    start = end - timedelta(days=365 * 3)
    price_loader = PriceLoader(YFinanceProvider())
    price_result = price_loader.fetch_universe(universe, start, end)

    # 2. Regime detection
    fred = FREDProvider(api_key=fred_key)
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
    regime_signal = detector.detect(as_of=today)

    # 3. Target allocation
    target_allocation = RegimeBasedTacticalStrategy().compute(regime_signal)

    # 4. Selection
    portfolio = TopNPerBucketStrategy(n_per_bucket=2).select(
        target_allocation, universe, price_result.prices
    )

    # 5. Portfolio initialization
    portfolio_state = PortfolioSimulator.initialize(
        target=portfolio,
        prices=price_result.prices,
        capital=INITIAL_CAPITAL,
        as_of=today,
    )

    # 6. Risk metrics
    weights = portfolio.as_dict()
    pf_returns = portfolio_returns(price_result.prices, weights)
    pf_levels = portfolio_levels(pf_returns)

    bench_returns = portfolio_returns(price_result.prices, BENCHMARK_60_40)
    bench_levels = portfolio_levels(bench_returns)

    risk_calc = HistoricalRiskCalculator()
    portfolio_metrics = risk_calc.compute(
        pf_levels, benchmark_prices=bench_levels, as_of=today
    )
    benchmark_metrics = risk_calc.compute(bench_levels, as_of=today)

    return PipelineState(
        today=today,
        universe=universe,
        prices=price_result.prices,
        n_successful=len(price_result.successful),
        n_failed=len(price_result.failed),
        regime_signal=regime_signal,
        target_allocation=target_allocation,
        portfolio=portfolio,
        portfolio_state=portfolio_state,
        portfolio_metrics=portfolio_metrics,
        benchmark_metrics=benchmark_metrics,
        portfolio_levels_series=pf_levels,
        benchmark_levels_series=bench_levels,
    )


def regime_color(regime_value: str) -> str:
    """Return a hex color associated with each regime, for visualization consistency."""
    palette = {
        "goldilocks": "#10b981",  # emerald
        "reflation": "#f59e0b",  # amber
        "stagflation": "#ef4444",  # red
        "disinflation_recession": "#3b82f6",  # blue
        "uncertain": "#6b7280",  # gray
    }
    return palette.get(regime_value, "#6b7280")


def neutral_tilt_dict() -> dict[str, float]:
    """Return the neutral tilt as a string-keyed dict for display."""
    return {ac.value: w for ac, w in NEUTRAL_TILT.items()}


_FR_MONTHS = {
    1: "janvier", 2: "fevrier", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "aout",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "decembre",
}


def format_date_fr(d: date) -> str:
    """Format a date as 'DD month YYYY' in French, OS-locale-independent."""
    month = _FR_MONTHS[d.month]
    return f"{d.day:02d} {month} {d.year}"