"""Utility functions for risk analytics."""

from __future__ import annotations

import pandas as pd


def portfolio_returns(
    prices: pd.DataFrame,
    weights: dict[str, float],
) -> pd.Series:
    """Compute time series of portfolio returns from per-asset prices.

    Assumes daily rebalancing to the target weights (a simplification that
    will be refined when the portfolio module implements realistic rebalancing).

    Args:
        prices: DataFrame with one column per ticker, indexed by date.
        weights: Mapping ticker -> target weight. Tickers absent from
            prices.columns are silently skipped. Remaining weights are
            renormalised to sum to 1.

    Returns:
        Daily returns of the portfolio. Empty if no overlap.
    """
    if not weights:
        return pd.Series(dtype=float)

    asset_returns = prices.pct_change().dropna(how="all")
    common = [t for t in weights if t in asset_returns.columns]
    if not common:
        return pd.Series(dtype=float)

    sub_weights = pd.Series({t: weights[t] for t in common}, dtype=float)
    total = float(sub_weights.sum())
    if total <= 0.0:
        return pd.Series(dtype=float)
    sub_weights = sub_weights / total

    aligned = asset_returns[common].dropna()
    return aligned.dot(sub_weights)


def portfolio_levels(returns: pd.Series, base: float = 100.0) -> pd.Series:
    """Convert a return series back into normalised price levels."""
    if returns.empty:
        return pd.Series(dtype=float)
    return base * (1.0 + returns).cumprod()
