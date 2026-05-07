"""Selection strategies: turn a TargetAllocation + Universe + prices into a Portfolio."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd
from loguru import logger

from bml.allocation.models import TargetAllocation
from bml.selection.models import Portfolio, PortfolioPosition
from bml.selection.scorer import AssetScorer, CompositeScorer
from bml.universe.asset import Asset, AssetClass
from bml.universe.universe import Universe


class SelectionStrategy(ABC):
    """Strategy interface for fund selection."""

    @abstractmethod
    def select(
        self,
        target: TargetAllocation,
        universe: Universe,
        prices: pd.DataFrame,
    ) -> Portfolio:
        """Construct a tradable Portfolio from a TargetAllocation."""


class TopNPerBucketStrategy(SelectionStrategy):
    """Select the top N assets per bucket via z-normalised composite scoring.

    Pipeline:
      1. For each non-zero bucket in the target allocation, find candidate
         assets (in universe AND with available price data).
      2. If a bucket has no candidates, redistribute its weight to cash and
         log a note.
      3. For each remaining bucket, score candidates with the configured
         AssetScorer, z-normalise within the bucket, and weight the metrics.
      4. Take the top N candidates by composite score, equal-weight them
         within the bucket.
      5. Renormalise final weights to sum exactly to 1.0.
    """

    DEFAULT_METRIC_WEIGHTS: ClassVar[dict[str, float]] = {
        "sharpe": 0.60,
        "neg_drawdown": 0.25,
        "neg_ter": 0.15,
    }

    def __init__(
        self,
        scorer: AssetScorer | None = None,
        n_per_bucket: int = 2,
        metric_weights: dict[str, float] | None = None,
    ) -> None:
        if n_per_bucket < 1:
            msg = "n_per_bucket must be >= 1"
            raise ValueError(msg)
        self._scorer = scorer or CompositeScorer()
        self._n = n_per_bucket
        self._weights = metric_weights or dict(self.DEFAULT_METRIC_WEIGHTS)

    def select(
        self,
        target: TargetAllocation,
        universe: Universe,
        prices: pd.DataFrame,
    ) -> Portfolio:
        notes: list[str] = []
        adjusted_weights = self._reroute_missing_buckets(target, universe, prices, notes)

        positions: list[PortfolioPosition] = []
        for bucket, weight in adjusted_weights.items():
            candidates = self._candidates_for(bucket, universe, prices)
            metrics_per_asset = {
                a.ticker: self._scorer.metrics(prices[a.ticker], a) for a in candidates
            }
            scores = self._aggregate_scores(metrics_per_asset)

            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self._n]
            n_chosen = len(top)
            per_asset_weight = weight / n_chosen

            for ticker, score in top:
                asset = next(a for a in candidates if a.ticker == ticker)
                positions.append(
                    PortfolioPosition(
                        asset=asset,
                        weight=per_asset_weight,
                        bucket=bucket,
                        score=round(score, 4),
                    )
                )

        positions = self._renormalise(positions)
        return Portfolio(
            as_of=target.as_of,
            positions=positions,
            target_allocation=target,
            notes=notes,
        )

    def _reroute_missing_buckets(
        self,
        target: TargetAllocation,
        universe: Universe,
        prices: pd.DataFrame,
        notes: list[str],
    ) -> dict[AssetClass, float]:
        """Detect buckets with no available candidates and reroute weight to cash."""
        adjusted: dict[AssetClass, float] = {}
        redistributed = 0.0

        for bw in target.buckets:
            if bw.weight <= 1e-9:
                continue
            candidates = self._candidates_for(bw.asset_class, universe, prices)
            if not candidates:
                logger.warning(
                    "No candidates for bucket {bucket}; rerouting {w:.1%} to cash",
                    bucket=bw.asset_class.value,
                    w=bw.weight,
                )
                notes.append(
                    f"No assets for {bw.asset_class.value}; rerouted {bw.weight:.1%} to cash."
                )
                redistributed += bw.weight
            else:
                adjusted[bw.asset_class] = bw.weight

        if redistributed > 0:
            cash_candidates = self._candidates_for(AssetClass.CASH, universe, prices)
            if not cash_candidates:
                msg = (
                    "Cannot redistribute to cash: no cash assets available in universe. "
                    "Add at least one cash ETF to the universe."
                )
                raise RuntimeError(msg)
            adjusted[AssetClass.CASH] = adjusted.get(AssetClass.CASH, 0.0) + redistributed

        return adjusted

    @staticmethod
    def _candidates_for(
        bucket: AssetClass,
        universe: Universe,
        prices: pd.DataFrame,
    ) -> list[Asset]:
        return [
            a
            for a in universe.by_class(bucket).assets
            if a.ticker in prices.columns and prices[a.ticker].dropna().shape[0] >= 60
        ]

    def _aggregate_scores(
        self,
        metrics_per_asset: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Z-normalise each metric within the peer group, then weight-combine."""
        if not metrics_per_asset:
            return {}
        if len(metrics_per_asset) == 1:
            ticker = next(iter(metrics_per_asset))
            metrics = metrics_per_asset[ticker]
            score = sum(self._weights[k] * metrics[k] for k in self._weights if k in metrics)
            return {ticker: score}

        scores: dict[str, float] = dict.fromkeys(metrics_per_asset, 0.0)
        for metric_name, weight in self._weights.items():
            values = [metrics_per_asset[t].get(metric_name, 0.0) for t in metrics_per_asset]
            n = len(values)
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            std = variance**0.5
            for ticker in metrics_per_asset:
                raw = metrics_per_asset[ticker].get(metric_name, 0.0)
                z = 0.0 if std == 0.0 else (raw - mean) / std
                scores[ticker] += weight * z
        return scores

    @staticmethod
    def _renormalise(positions: list[PortfolioPosition]) -> list[PortfolioPosition]:
        """Ensure weights sum exactly to 1.0 by absorbing residual into last position."""
        if not positions:
            return positions
        total = sum(p.weight for p in positions)
        if total <= 0:
            return positions
        rescaled = [
            PortfolioPosition(
                asset=p.asset,
                weight=p.weight / total,
                bucket=p.bucket,
                score=p.score,
            )
            for p in positions
        ]
        residual = 1.0 - sum(p.weight for p in rescaled)
        if abs(residual) > 1e-12:
            last = rescaled[-1]
            rescaled[-1] = PortfolioPosition(
                asset=last.asset,
                weight=last.weight + residual,
                bucket=last.bucket,
                score=last.score,
            )
        return rescaled
