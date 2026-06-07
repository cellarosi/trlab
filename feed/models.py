"""Provider-independent market data feed return models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OptionRight(str, Enum):
    """Normalized option contract right values."""

    CALL = "call"
    PUT = "put"


class Bar(BaseModel):
    """One provider-independent OHLCV market data interval."""

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
    """One normalized call or put option-chain contract row."""

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
    """Provider-independent option chain for an underlying symbol."""

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