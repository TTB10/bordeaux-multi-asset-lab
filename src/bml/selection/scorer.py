"""Asset scoring: from a price history, compute multi-criteria metrics.

Scorers return raw metrics (higher = better for each one). The selection
strategy is responsible for aggregating these metrics into a single score
across a peer group, typically via z-score normalization.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from bml.universe.asset import Asset


class AssetScorer(ABC):
    """Strategy interface for scoring an individual asset."""

    @abstractmethod
    def metrics(self, prices: pd.Series, asset: Asset) -> dict[str, float]:
        """Compute raw metrics from a price history.

        Args:
            prices: Daily price series, sorted ascending, no leading NaN.
            asset: The Asset object (used for static fields like TER).

        Returns:
            Dict of metric_name -> value. Higher = better convention.
        """


class CompositeScorer(AssetScorer):
    """Standard multi-criteria scorer for fund selection.

    Returns three metrics (all higher = better):
      - sharpe: annualized Sharpe ratio over the available history
      - neg_drawdown: negated max drawdown (so higher = less drawdown)
      - neg_ter: negated total expense ratio (so higher = cheaper)

    The strategy z-normalises and combines these with configurable weights.
    """

    MIN_OBS = 60  # ~3 months of daily data

    def metrics(self, prices: pd.Series, asset: Asset) -> dict[str, float]:
        clean = prices.dropna()
        if len(clean) < self.MIN_OBS:
            # Not enough data: return neutral values that won't dominate
            return {
                "sharpe": 0.0,
                "neg_drawdown": 0.0,
                "neg_ter": -asset.ter,
            }

        returns = clean.pct_change().dropna()
        if returns.std() == 0.0:
            sharpe = 0.0
        else:
            sharpe = float(returns.mean() * 252.0 / (returns.std() * np.sqrt(252.0)))

        cum = (1.0 + returns).cumprod()
        max_dd = float((cum / cum.cummax() - 1.0).min())  # negative or 0

        return {
            "sharpe": sharpe,
            "neg_drawdown": -abs(max_dd),  # less drawdown -> higher score
            "neg_ter": -asset.ter,
        }
