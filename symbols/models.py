"""Validated symbol models and loading utilities."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator


class InstrumentType(str, Enum):
    """Supported financial instrument product types."""

    INDEX = "INDEX"
    ETF = "ETF"
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class Symbol(BaseModel):
    """A minimal financial instrument root/product."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    type: InstrumentType
    contracts: list[str]

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
