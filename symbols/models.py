"""Validated symbol models and loading utilities."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class InstrumentType(str, Enum):
    """Supported financial instrument product types."""

    INDEX = "INDEX"
    ETF = "ETF"
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class SessionDay(BaseModel):
    """Represents trading hours for a specific day."""

    model_config = ConfigDict(extra="forbid")

    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class Sessions(BaseModel):
    """Represents trading sessions for a symbol."""

    model_config = ConfigDict(extra="forbid")

    timezone: str
    monday: SessionDay | None = None
    tuesday: SessionDay | None = None
    wednesday: SessionDay | None = None
    thursday: SessionDay | None = None
    friday: SessionDay | None = None
    saturday: SessionDay | None = None
    sunday: SessionDay | None = None


class Symbol(BaseModel):
    """A minimal financial instrument root/product."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    type: InstrumentType
    contracts: list[str]
    sessions: Sessions

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_non_empty(cls, value: str) -> str:
        ticker = value.strip()
        if not ticker:
            raise ValueError("ticker must be non-empty")
        return ticker

    @field_validator("contracts")
    @classmethod
    def contracts_must_be_non_empty_strings(cls, value: list[str]) -> list[str]:
        contracts = [contract.strip() for contract in value]
        if any(not contract for contract in contracts):
            raise ValueError("contracts must contain only non-empty strings")
        return contracts


def load_symbols(path: str | Path) -> list[Symbol]:
    """Load and validate a JSON array of symbols."""

    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    return TypeAdapter(list[Symbol]).validate_python(data)