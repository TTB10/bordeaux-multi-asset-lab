"""Domain models for risk metrics."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RiskMetrics(BaseModel):
    """Bundle of risk metrics computed over a price history.

    Attributes:
        as_of: Reference date for the computation.
        horizon_days: Number of daily observations used.
        annual_return: Annualised compound return.
        annual_volatility: Annualised volatility (daily std * sqrt(252)).
        sharpe_ratio: (annual_return - risk_free) / annual_volatility.
        max_drawdown: Maximum peak-to-trough loss (negative or zero).
        var_95: 5% quantile of daily returns (typically negative).
        cvar_95: Mean of returns at or below var_95.
        beta: Sensitivity to a benchmark. None if no benchmark provided.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: date
    horizon_days: int = Field(ge=0)

    annual_return: float
    annual_volatility: float = Field(ge=0.0)
    sharpe_ratio: float
    max_drawdown: float = Field(le=0.0)
    var_95: float
    cvar_95: float
    beta: float | None = None

    def summary(self) -> str:
        """Human-readable summary for logs and reports."""
        beta_str = f"{self.beta:+.2f}" if self.beta is not None else "n/a"
        return (
            f"return={self.annual_return:+.2%}  vol={self.annual_volatility:.2%}  "
            f"sharpe={self.sharpe_ratio:+.2f}  maxDD={self.max_drawdown:+.2%}  "
            f"VaR95={self.var_95:+.2%}  CVaR95={self.cvar_95:+.2%}  beta={beta_str}"
        )
