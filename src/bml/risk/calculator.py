"""Risk calculators turn a price history into a RiskMetrics bundle."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import numpy as np
import pandas as pd

from bml.risk.models import RiskMetrics

TRADING_DAYS_PER_YEAR = 252


class RiskCalculator(ABC):
    """Strategy interface for computing risk metrics."""

    @abstractmethod
    def compute(
        self,
        prices: pd.Series,
        benchmark_prices: pd.Series | None = None,
        as_of: date | None = None,
    ) -> RiskMetrics:
        """Compute risk metrics for a price history."""


class HistoricalRiskCalculator(RiskCalculator):
    """Standard historical risk metrics: vol, Sharpe, drawdown, VaR, CVaR, Beta.

    All metrics are derived from the empirical distribution of daily returns,
    no parametric assumption (no Gaussian assumption).
    """

    DEFAULT_RISK_FREE_RATE = 0.025  # 2.5% annual, ~ EUR overnight rate
    DEFAULT_VAR_ALPHA = 0.05  # 95% confidence VaR
    MIN_OBSERVATIONS = 30

    def __init__(
        self,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        var_alpha: float = DEFAULT_VAR_ALPHA,
    ) -> None:
        if not 0.0 < var_alpha < 0.5:
            msg = "var_alpha must be in (0, 0.5)"
            raise ValueError(msg)
        self._rf = risk_free_rate
        self._alpha = var_alpha

    def compute(
        self,
        prices: pd.Series,
        benchmark_prices: pd.Series | None = None,
        as_of: date | None = None,
    ) -> RiskMetrics:
        clean = prices.dropna()
        as_of = as_of or date.today()

        if len(clean) < self.MIN_OBSERVATIONS:
            return self._neutral_metrics(as_of, len(clean))

        returns = clean.pct_change().dropna()
        annual_return = self._annual_return(returns)
        annual_vol = self._annual_volatility(returns)
        sharpe = self._sharpe(annual_return, annual_vol)
        max_dd = self._max_drawdown(returns)
        var = float(returns.quantile(self._alpha))
        cvar_series = returns[returns <= var]
        cvar = float(cvar_series.mean()) if len(cvar_series) > 0 else var
        beta = self._beta(returns, benchmark_prices) if benchmark_prices is not None else None

        return RiskMetrics(
            as_of=as_of,
            horizon_days=len(returns),
            annual_return=annual_return,
            annual_volatility=annual_vol,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            var_95=var,
            cvar_95=cvar,
            beta=beta,
        )

    @staticmethod
    def _neutral_metrics(as_of: date, horizon: int) -> RiskMetrics:
        return RiskMetrics(
            as_of=as_of,
            horizon_days=horizon,
            annual_return=0.0,
            annual_volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            var_95=0.0,
            cvar_95=0.0,
            beta=None,
        )

    @staticmethod
    def _annual_return(returns: pd.Series) -> float:
        if len(returns) == 0:
            return 0.0
        cum = float((1.0 + returns).prod())
        years = len(returns) / TRADING_DAYS_PER_YEAR
        if years <= 0:
            return 0.0
        return float(cum ** (1.0 / years) - 1.0)

    @staticmethod
    def _annual_volatility(returns: pd.Series) -> float:
        std = float(returns.std())
        return std * float(np.sqrt(TRADING_DAYS_PER_YEAR))

    def _sharpe(self, annual_return: float, annual_vol: float) -> float:
        if annual_vol <= 0.0:
            return 0.0
        return (annual_return - self._rf) / annual_vol

    @staticmethod
    def _max_drawdown(returns: pd.Series) -> float:
        cum = (1.0 + returns).cumprod()
        peak = cum.cummax()
        dd = cum / peak - 1.0
        return float(dd.min())

    @staticmethod
    def _beta(asset_returns: pd.Series, benchmark_prices: pd.Series) -> float | None:
        bench_clean = benchmark_prices.dropna()
        if len(bench_clean) < 10:
            return None
        bench_returns = bench_clean.pct_change().dropna()

        aligned = pd.DataFrame({"asset": asset_returns, "bench": bench_returns}).dropna()
        if len(aligned) < 10:
            return None
        bench_var = float(aligned["bench"].var())
        if bench_var <= 0.0:
            return None
        cov = float(aligned[["asset", "bench"]].cov().iloc[0, 1])
        return cov / bench_var
