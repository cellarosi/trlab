"""
Provider-independent market data feed interface.

Design Rationale:
- `DataFeed` acts as the universal, provider-independent contract for all market 
  data retrieval operations.
- Establishes a standard surface for four core async methods (`get_current_bar`, 
  `get_historical_bars`, `get_current_option_chain`, `get_historical_option_chain`), 
  plus `get_option_expirations`.
- Uses standard feed return models (`Bar`, `OptionChain`) rather than 
  provider-native payloads to ensure downstream consumers are decoupled from 
  specific provider quirks.
- Default implementations raise `UnsupportedCapabilityError`. Concrete provider 
  adapters override only the methods they support, inheriting the default error 
  for unsupported ones. This avoids the need to fake unsupported methods or write 
  boilerplate "not implemented" code in every adapter.
- The `supports` method uses introspection to check if a concrete feed overrides 
  a base method, allowing the Scheduler/Engine to gracefully query capability 
  before invocation, instead of relying solely on exception handling.
"""

from __future__ import annotations

from datetime import date, datetime

from feed.errors import UnsupportedCapabilityError
from feed.models import Bar, OptionChain


DateLike = date | datetime
"""Type alias for date or datetime values used across the feed interface."""


class DataFeed:
    """Base class for provider-specific market data feeds."""

    _operations = frozenset(
        {
            "get_current_bar",
            "get_current_option_chain",
            "get_historical_bars",
            "get_historical_option_chain",
            "get_option_expirations",
        }
    )

    def supports(self, operation: str) -> bool:
        """Return whether this feed overrides a known feed operation.
        
        Why this matters: Allows callers (like the scheduler or analysis scripts) 
        to explicitly check if a provider supports a feature before attempting it, 
        enabling graceful fallbacks or feature toggling without catching exceptions.
        """
        if operation not in self._operations:
            return False
        return getattr(type(self), operation, None) is not getattr(DataFeed, operation)

    async def get_current_bar(
        self,
        ticker: str,
        interval: str | None = None,
    ) -> Bar:
        """Return the current bar for a provider-ready ticker."""
        raise UnsupportedCapabilityError.for_operation(type(self).__name__, "get_current_bar")

    async def get_current_option_chain(
        self,
        ticker: str,
        expiration: date | None = None,
    ) -> OptionChain:
        """Return the current option chain for a provider-ready underlying ticker."""
        raise UnsupportedCapabilityError.for_operation(
            type(self).__name__, "get_current_option_chain"
        )

    async def get_historical_bars(
        self,
        ticker: str,
        start: DateLike,
        end: DateLike,
        interval: str | None = None,
    ) -> list[Bar]:
        """Return historical bars for a provider-ready ticker and date/time range."""
        raise UnsupportedCapabilityError.for_operation(type(self).__name__, "get_historical_bars")

    async def get_historical_option_chain(
        self,
        ticker: str,
        as_of: DateLike,
        expiration: date | None = None,
    ) -> OptionChain:
        """Return a historical option chain for a provider-ready ticker as of a date/time."""
        raise UnsupportedCapabilityError.for_operation(
            type(self).__name__, "get_historical_option_chain"
        )

    async def get_option_expirations(self, ticker: str) -> list[date]:
        """Return the list of available option expiration dates for a ticker."""
        raise UnsupportedCapabilityError.for_operation(
            type(self).__name__, "get_option_expirations"
        )