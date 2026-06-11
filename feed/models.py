"""
Provider-independent market data feed return models.

Design Rationale:
- These models form the canonical, normalized data contract between any provider 
  adapter (Yahoo, Tiingo, etc.) and the rest of the application (e.g., the Scheduler).
- Strict validation (`extra="forbid"`) ensures that downstream consumers never 
  accidentally rely on provider-specific, undocumented fields that might leak into 
  the payload. This enforces true provider independence.
- `Decimal` is used for all price/volume metrics to prevent floating-point precision 
  loss, which is critical for financial calculations and aggregations.
- `OptionChain` groups individual `OptionContract` rows, fulfilling the requirement 
  to return a structured, hierarchical representation of options data rather than 
  a flat, un-grouped list.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OptionRight(str, Enum):
    """Normalized option contract right values.
    
    Why an Enum: Restricts valid values to strictly 'call' or 'put', preventing 
    invalid or normalized variations (e.g., 'C', 'P', 'Call') from propagating 
    through the system.
    """
    CALL = "call"
    PUT = "put"


class Bar(BaseModel):
    """One provider-independent OHLCV market data interval.
    
    Used by both `get_current_bar` and `get_historical_bars` to ensure a uniform 
    representation of price action across different timeframes and providers.
    """
    model_config = ConfigDict(extra="forbid")

    ticker: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(ge=0)
    interval: str | None = None

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_non_empty(cls, value: str) -> str:
        ticker = value.strip()
        if not ticker:
            raise ValueError("ticker must be non-empty")
        return ticker


class OptionContract(BaseModel):
    """One normalized call or put option-chain contract row.
    
    Contains both mandatory structural data (underlying, expiration, strike, right) 
    and optional normalized market data (Greeks, volume, open interest). Optional 
    fields default to None to gracefully handle providers that do not supply them.
    """
    model_config = ConfigDict(extra="forbid")

    underlying_ticker: str
    option_ticker: str
    expiration: date
    strike: Decimal
    right: OptionRight
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    mark: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)

    @field_validator("underlying_ticker", "option_ticker")
    @classmethod
    def tickers_must_be_non_empty(cls, value: str) -> str:
        ticker = value.strip()
        if not ticker:
            raise ValueError("ticker fields must be non-empty")
        return ticker


class OptionChain(BaseModel):
    """Provider-independent option chain for an underlying symbol.
    
    Groups multiple `OptionContract` rows under a common `underlying_ticker` and 
    `as_of` timestamp, optionally filtered by a specific `expiration`. This 
    aggregation is required to fulfill the "all expiration all strike" mandate 
    cleanly, allowing the caller to receive a single cohesive object rather than 
    managing a disparate list of contracts.
    """
    model_config = ConfigDict(extra="forbid")

    underlying_ticker: str
    as_of: datetime
    expiration: date | None = None
    contracts: list[OptionContract] = Field(default_factory=list)

    @field_validator("underlying_ticker")
    @classmethod
    def underlying_ticker_must_be_non_empty(cls, value: str) -> str:
        ticker = value.strip()
        if not ticker:
            raise ValueError("underlying_ticker must be non-empty")
        return ticker