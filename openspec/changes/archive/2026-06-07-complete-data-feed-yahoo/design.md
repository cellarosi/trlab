## Context

The feed package now has standard return models and a provider-neutral `DataFeed` interface, but `YahooFeed` still inherits every unsupported base method. The current interface accepts `Symbol` objects, which mixes catalog/mapping concerns into provider adapters. This change makes the feed boundary string-based: callers pass a ticker that has already been mapped into the provider-compatible identifier, and YahooFeed only retrieves and normalizes data for that ticker.

## Goals / Non-Goals

**Goals:**
- Implement `YahooFeed.get_current_bar`, `YahooFeed.get_historical_bars`, and `YahooFeed.get_current_option_chain` with standard `Bar` and `OptionChain` return models.
- Update `DataFeed` method signatures and standard feed models to use ticker strings at the feed boundary instead of `Symbol` objects.
- Preserve `YahooFeed.get_historical_option_chain` as unsupported so `supports()` accurately reports only the implemented Yahoo operations.
- Treat every ticker passed to YahooFeed as already provider-compatible; YahooFeed MUST NOT translate roots such as `ES` into provider-specific symbols.
- Keep imports lazy so importing `feed` does not eagerly require or load Yahoo-specific libraries.
- Add tests by mocking `yfinance.Ticker` rather than using live network calls.

**Non-Goals:**
- No historical option-chain retrieval.
- No streaming, caching, retries, persistence, or real-time market-data entitlement handling.
- No new provider-specific data models exposed through the public `feed` API.
- No symbol catalog lookup, contract selection, or root-to-provider ticker mapping inside YahooFeed.
- No guarantee that Yahoo delayed/current data is real-time.

## Decisions

### Implement Yahoo as a partial provider adapter

`YahooFeed` will override only the three Yahoo-backed operations: current bar, historical bars, and current option chain. It will inherit `DataFeed.get_historical_option_chain`, so `supports("get_historical_option_chain")` remains false and callers can detect the limitation before invoking it.

Alternative considered: overriding historical option chains to raise directly in `YahooFeed`. Inheriting the base method is simpler and keeps `supports()` behavior consistent with other unsupported operations.

### Use lazy yfinance loading

`YahooFeed` should lazily import `yfinance` and construct `yfinance.Ticker` when an implemented method is called. Tests should mock the lazy `yfinance.Ticker` construction rather than adding a production client-factory abstraction. This preserves the existing public import behavior where `import feed` does not import provider-specific dependencies while keeping the adapter simple.

The adapter will keep small helper methods for this boundary: one helper centralizes lazy `yfinance.Ticker` construction, and one helper wraps Yahoo calls so provider exceptions are consistently converted into normalized feed-layer errors.

Alternative considered: importing the Yahoo package at module import time. That makes failures immediate, but it breaks provider-independent imports and complicates environments that only need interfaces or tests.

### Keep ticker mapping outside DataFeed

`DataFeed` methods should accept `ticker: str`, not `Symbol`. The ticker is the exact provider-ready identifier that the adapter should request. For an ETF this can be `SPY`; for a futures bar it can be a concrete tradable/provider identifier such as `ESZ5`; for an option chain it is the underlying ticker such as `SPY` plus the method's `expiration` parameter. Any root-to-contract or catalog mapping happens before the feed call.

Alternative considered: resolving `Symbol.contracts[0]` inside YahooFeed. That is ambiguous for futures with multiple contracts and puts mapping policy in the wrong layer.

### Normalize provider payloads at the adapter boundary

Yahoo rows should be converted into `Bar`, `OptionContract`, and `OptionChain` before returning, using ticker string fields in the standard models. Empty data should raise `DataUnavailableError`; provider exceptions should become normalized feed errors such as `NetworkError`, `DataFeedTimeoutError`, or `NormalizationError` depending on failure type.

Alternative considered: returning provider-native dictionaries or data frames. That would be simpler initially, but it would violate the standard feed return contract.

## Risks / Trade-offs

- Yahoo payload shape changes → Mitigation: keep normalization isolated in helper methods and cover expected shapes with fake-client tests.
- The provider dependency may not be installed → Mitigation: lazy import and raise a normalized configuration/provider error only when Yahoo-backed methods are called.
- Current quote data may be delayed or missing fields → Mitigation: document current data as Yahoo delayed/current data and raise `DataUnavailableError` when required OHLCV fields are absent.
- Caller-provided tickers may not be recognized by Yahoo → Mitigation: validate non-empty ticker strings locally and surface provider empty/error responses as normalized feed errors.

## Migration Plan

- Add the Yahoo client dependency using the project package manager during implementation if it is not already available.
- Update the base `DataFeed` method signatures and feed return models from `Symbol` fields to ticker string fields before implementing Yahoo methods.
- Test the adapter by mocking lazy `yfinance.Ticker` construction so tests remain deterministic and offline.
- Existing callers that only import `feed` should continue to work without eagerly loading the Yahoo client package.
- Existing callers that relied on Yahoo operations raising unsupported errors should switch to `supports()` or handle implemented return models for the three newly supported operations.

## Open Questions

None.