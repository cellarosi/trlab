## Why

The feed layer currently has a Yahoo-backed adapter but no Tiingo-backed source for authenticated end-of-day market data. Adding Tiingo support gives callers a second provider option for current and historical OHLCV bars while preserving the existing provider-independent `DataFeed` API.

## What Changes

- Add a `TiingoFeed` provider adapter that extends `DataFeed`.
- Implement only `get_current_bar` and `get_historical_bars` for Tiingo end-of-day data.
- Require callers to pass a Tiingo API token explicitly to `TiingoFeed` without hard-coding secrets.
- Normalize Tiingo end-of-day API payloads into standard `Bar` models and normalized `DataFeedError` subtypes.
- Export `TiingoFeed` from the public `feed` package without requiring Tiingo-specific dependencies or credentials at import time.
- Add a live smoke-test script for real-time/manual Tiingo checks that obtains a token from the user and passes it to `TiingoFeed`.
- Add automated tests for adapter behavior, token handling, normalization, capability reporting, and error mapping.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `data-feed`: Add Tiingo as a supported feed adapter for current and historical bar retrieval.

## Impact

- Affected code: `feed/`, `tests/test_feed.py`, and `scripts/`.
- Public API: `feed.TiingoFeed` becomes importable alongside `YahooFeed`.
- Configuration: Tiingo operations require an API token passed as an explicit `TiingoFeed` constructor argument; callers choose how to retrieve the token before constructing the feed.
- External systems: Tiingo end-of-day REST API documented at `https://www.tiingo.com/documentation/end-of-day`.
- Dependencies: Prefer the standard library HTTP stack unless implementation identifies a strong need for a new dependency.