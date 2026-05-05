"""Domain model for a single investable asset (typically a UCITS ETF or fund)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssetClass(StrEnum):
    """High-level asset class taxonomy used across the framework."""

    EQUITY_DM = "equity_developed_markets"
    EQUITY_EM = "equity_emerging_markets"
    GOVERNMENT_BOND = "government_bond"
    CREDIT_IG = "credit_investment_grade"
    CREDIT_HY = "credit_high_yield"
    GOLD = "gold"
    COMMODITY = "broad_commodity"
    REAL_ESTATE = "real_estate"
    CASH = "cash"
    LISTED_PE = "listed_private_equity"
    INFRASTRUCTURE = "infrastructure"
    MANAGED_FUTURES = "managed_futures"
    CONVERTIBLE = "convertible_bond"


class Region(StrEnum):
    """Geographic region of the underlying exposure."""

    GLOBAL = "global"
    USA = "usa"
    EUROPE = "europe"
    EUROZONE = "eurozone"
    UK = "uk"
    JAPAN = "japan"
    EMERGING = "emerging"
    ASIA_EX_JAPAN = "asia_ex_japan"


class Asset(BaseModel):
    """An investable instrument in the BML universe.

    Attributes:
        ticker: Exchange ticker (e.g. "IWDA.AS").
        isin: International Securities Identification Number (unique).
        name: Human-readable name.
        asset_class: High-level asset class.
        region: Geographic exposure.
        currency: Base currency (ISO 4217).
        ter: Total Expense Ratio in decimal form (e.g. 0.0020 for 0.20%).
        issuer: Asset manager issuing the fund (iShares, Vanguard, ...).
        hedged: True if the share class is currency-hedged to the base ccy.
        inception_date: Optional ISO date of fund inception.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str = Field(min_length=1)
    isin: str = Field(min_length=12, max_length=12, pattern=r"^[A-Z0-9]{12}$")
    name: str
    asset_class: AssetClass
    region: Region
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    ter: float = Field(ge=0.0, le=0.05)
    issuer: str | None = None
    hedged: bool = False
    inception_date: str | None = None

    def __str__(self) -> str:
        return f"{self.ticker} ({self.name})"
