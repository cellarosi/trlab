"""Provider-independent market data feed interface."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from symbols.models import Symbol

from feed.errors import UnsupportedCapabilityError


DateLike = date | datetime


class DataFeed:
    """Base class for provider-specific market data feeds."""

    _operations = frozenset(
        {
            "get_current_bar",
            "get_current_option_chain",
            "get_historical_bars",
            "get_historical_option_chain",
        }
    )

    def supports(self, operation: str) -> bool:
        """Return whether this feed overrides a known feed operation."""

        if operation not in self._operations:
            return False
        return getattr(type(self), operation, None) is not getattr(DataFeed, operation)

    async def get_current_bar(
        self,
        symbol: Symbol,
        interval: str | None = None,
    ) -> Any:
        """Return the current bar for a symbol."""

        raise UnsupportedCapabilityError.for_operation(type(self).__name__, "get_current_bar")

    async def get_current_option_chain(
        self,
        symbol: Symbol,
        expiration: date | None = None,
    ) -> Any:
        """Return the current option chain for a symbol."""

        raise UnsupportedCapabilityError.for_operation(
            type(self).__name__, "get_current_option_chain"
        )

    async def get_historical_bars(
        self,
        symbol: Symbol,
        start: DateLike,
        end: DateLike,
        interval: str | None = None,
    ) -> Any:
        """Return historical bars for a symbol and date/time range."""

        raise UnsupportedCapabilityError.for_operation(type(self).__name__, "get_historical_bars")

    async def get_historical_option_chain(
        self,
        symbol: Symbol,
        as_of: DateLike,
        expiration: date | None = None,
    ) -> Any:
        """Return a historical option chain for a symbol as of a date/time."""

        raise UnsupportedCapabilityError.for_operation(
            type(self).__name__, "get_historical_option_chain"
        )