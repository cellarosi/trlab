## Why

The project now has a minimal symbol catalog, but no provider-independent way to ask for market data. A small async `DataFeed` base interface establishes a stable contract before adding Yahoo as the first concrete feed.

## What Changes

- Add a new `feed/` package for market data feed abstractions and provider adapters.
- Introduce an async `DataFeed` base class with a uniform public API for current bars, current option chains, historical bars, and historical option chains.
- Provide default unsupported implementations in `DataFeed` so concrete feeds override only the operations they support.
- Add a `supports()` capability check derived from whether a feed overrides the corresponding `DataFeed` method.
- Define normalized feed errors for unsupported capabilities and request/provider failures such as missing provider mappings, unavailable data, entitlement failures, rate limits, network failures, and normalization failures.
- Add `YahooFeed` as the first concrete feed, extending `DataFeed` and declaring support only by overriding the operations implemented in this change.
- Keep concrete data retrieval and provider library integration minimal and scoped to the interface/provider skeleton for this change.

## Capabilities

### New Capabilities
- `data-feed`: Defines the async market data feed interface, capability detection behavior, normalized error semantics, and the first Yahoo feed adapter skeleton.

### Modified Capabilities

None.

## Impact

- Adds a new `feed/` package.
- Introduces a provider-independent API surface that future feeds such as Polygon, IBKR, Databento, or local CSV can extend.
- Establishes async method signatures and normalized error semantics before implementing broader provider integrations.
- Does not require new third-party dependencies for the interface skeleton.
- Does not change existing `symbol-catalog` requirements in this change.
