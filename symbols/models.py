"""
Validated symbol models and loading utilities.

Design Rationale:
- Defines the canonical `Symbol` catalog model for financial instrument roots/products.
- Uses strict Pydantic validation to ensure that only supported `InstrumentType` 
  values are accepted, and that `contracts` arrays contain only non-empty strings.
- The `contracts` field is intentionally a list of strings (identifiers), not 
  fully expanded instrument records. This keeps the catalog lightweight and defers 
  heavy data loading to the `feed` package when specific contract data is requested.
- `Sessions` allows tracking of trading hours, which is critical for accurate 
  historical range calculations (e.g., knowing if a gap is an overnight gap vs. 
  a weekend gap).
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class InstrumentType(str, Enum):
    """Supported financial instrument product types.
    
    Why an Enum: Restricts the domain to known, manageable instrument classes, 
    preventing invalid or arbitrary types from being loaded into the catalog.
    """
    INDEX = "INDEX"
    ETF = "ETF"
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class SessionDay(BaseModel):
    """Represents trading hours for a specific day.
    
    Strict string pattern validation ensures times are in `HH:MM` format, 
    preventing malformed time strings from breaking session logic downstream.
    """
    model_config = ConfigDict(extra="forbid")

    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class Sessions(BaseModel):
    """Represents trading sessions for a symbol.
    
    Provides timezone-aware daily session definitions. Optional days allow 
    flexible modeling of instruments that don't trade 24/7 or trade on specific 
    days (e.g., futures with Sunday evening opens).
    """
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
    """A minimal financial instrument root/product.
    
    Serves as the master catalog entry. It links a ticker to its instrument type, 
    its associated contracts (for futures/options), and its trading sessions. 
    This centralizes metadata so the `feed` package only needs to deal with 
    "provider-ready" tickers, while the catalog handles the business logic of 
    what those tickers represent.
    """
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
    """Load and validate a JSON array of symbols.
    
    Why this function: Centralizes file reading and Pydantic `TypeAdapter` 
    validation. If any single entry in the JSON file is invalid, the entire 
    load fails fast, preventing the application from running with a partially 
    corrupted or invalid symbol catalog.
    """
    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    return TypeAdapter(list[Symbol]).validate_python(data)