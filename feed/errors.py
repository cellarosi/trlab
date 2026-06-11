"""
Normalized market data feed exceptions.

Design Rationale:
- Establishes a clear, provider-independent error hierarchy rooted at `DataFeedError`.
- Allows downstream code (like the Scheduler's "Log and Skip" or analysis scripts) 
  to catch and handle specific failure modes (e.g., `RateLimitError`, `DataUnavailableError`) 
  without needing to parse provider-specific exception strings or classes.
- Explicitly separates "Operation is not implemented by this feed" (`UnsupportedCapabilityError`) 
  from "Operation is supported, but this specific request failed" (all other subtypes).
"""

from __future__ import annotations


class DataFeedError(Exception):
    """Base exception for normalized market data feed failures."""


class UnsupportedCapabilityError(DataFeedError):
    """Raised when a feed operation is not implemented by the feed.
    
    Why it exists: Enables the `DataFeed.supports()` check. If a feed doesn't 
    override a method, this error is raised, signaling to the caller that they 
    should not attempt this operation with this specific provider.
    """

    @classmethod
    def for_operation(cls, feed_name: str, operation: str) -> "UnsupportedCapabilityError":
        return cls(f"{feed_name} does not support {operation}")


class MissingProviderMappingError(DataFeedError):
    """Raised when a symbol lacks a mapping for the requested provider."""


class UnsupportedInstrumentError(DataFeedError):
    """Raised when a provider cannot serve the requested instrument type."""


class DataUnavailableError(DataFeedError):
    """Raised when requested data is unavailable from the provider."""


class DataFeedAuthenticationError(DataFeedError):
    """Raised when provider authentication fails."""


class EntitlementError(DataFeedError):
    """Raised when provider permissions do not allow the request."""


class RateLimitError(DataFeedError):
    """Raised when a provider rate limit prevents fulfilling the request."""


class NetworkError(DataFeedError):
    """Raised when network communication with a provider fails."""


class DataFeedTimeoutError(DataFeedError):
    """Raised when a provider request times out."""


class NormalizationError(DataFeedError):
    """Raised when provider data cannot be normalized."""