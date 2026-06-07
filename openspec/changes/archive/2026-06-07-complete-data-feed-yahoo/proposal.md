## Why

`YahooFeed` currently exists only as a skeleton, so callers can detect the provider but cannot retrieve any market data through the standard `DataFeed` interface. Implementing Yahoo's available operations now makes the feed layer usable while also simplifying the feed boundary so providers receive already-mapped ticker strings instead of symbol catalog objects.

## What Changes

- Update `DataFeed` operation inputs to accept `ticker: str` instead of `Symbol`, leaving provider-specific ticker mapping outside the feed adapter.
- Implement `YahooFeed.get_current_bar` to return a standard `Bar` for an already Yahoo-compatible ticker using Yahoo's delayed/current market data.
- Implement `YahooFeed.get_historical_bars` to return `list[Bar]` for an already Yahoo-compatible ticker, requested date or datetime range, and interval.
- Implement `YahooFeed.get_current_option_chain` to return an `OptionChain` with normalized call and put `OptionContract` rows for an underlying ticker and optional expiration.
- Keep `YahooFeed.get_historical_option_chain` unsupported because Yahoo does not provide a historical option-chain method in scope for this adapter.
- Normalize Yahoo provider failures and empty/unusable responses into existing feed errors instead of leaking provider-native exceptions or payloads.
- Add tests around Yahoo method support, normalization, lazy provider dependency loading, and unsupported historical option-chain behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `data-feed`: DataFeed inputs change from `Symbol` objects to generic provider-ready ticker strings, and YahooFeed changes from a skeleton provider adapter to a partial provider implementation for current bars, historical bars, and current option chains while retaining unsupported behavior for historical option chains.

## Impact

- Affects `feed/yahoo.py` provider adapter behavior and support detection.
- May add or require a Yahoo provider client dependency, loaded lazily so importing `feed` remains provider-dependency-light.
- Updates standard feed models and operation annotations to carry ticker strings instead of `Symbol` objects at the feed boundary.
- Uses existing `Bar`, `OptionChain`, `OptionContract`, `OptionRight`, and normalized feed error models.
- Adds tests for Yahoo normalization without requiring live network calls.