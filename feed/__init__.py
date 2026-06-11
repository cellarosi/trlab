"""
Public market data feed API.

Design Rationale:
- Acts as the public, provider-independent facade for the entire feed package.
- Intentionally re-exports base classes, models, errors, and concrete feeds.
- Designed to be "provider-light": importing this module does NOT instantiate 
  or require third-party provider dependencies (like `yfinance`) until a 
  specific provider operation is actually invoked, ensuring clean, fast imports 
  across the application.
"""

from feed.base import DataFeed
from feed.errors import (
    DataFeedAuthenticationError,
    DataFeedError,
    DataFeedTimeoutError,
    DataUnavailableError,
    EntitlementError,
    MissingProviderMappingError,
    NetworkError,
    NormalizationError,
    RateLimitError,
    UnsupportedCapabilityError,
    UnsupportedInstrumentError,
)
from feed.models import Bar, OptionChain, OptionContract, OptionRight
from feed.tiingo import TiingoFeed
from feed.yahoo import YahooFeed

__all__ = [
    "Bar",
    "DataFeed",
    "DataFeedAuthenticationError",
    "DataFeedError",
    "DataFeedTimeoutError",
    "DataUnavailableError",
    "EntitlementError",
    "MissingProviderMappingError",
    "NetworkError",
    "OptionChain",
    "OptionContract",
    "OptionRight",
    "NormalizationError",
    "RateLimitError",
    "UnsupportedCapabilityError",
    "UnsupportedInstrumentError",
    "TiingoFeed",
    "YahooFeed",
]