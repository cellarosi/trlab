"""Public market data feed API."""

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
from feed.yahoo import YahooFeed

__all__ = [
    "DataFeed",
    "DataFeedAuthenticationError",
    "DataFeedError",
    "DataFeedTimeoutError",
    "DataUnavailableError",
    "EntitlementError",
    "MissingProviderMappingError",
    "NetworkError",
    "NormalizationError",
    "RateLimitError",
    "UnsupportedCapabilityError",
    "UnsupportedInstrumentError",
    "YahooFeed",
]