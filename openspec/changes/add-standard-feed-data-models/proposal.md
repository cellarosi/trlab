## Why

The `DataFeed` interface currently defines provider-independent operations but leaves return types as broad, provider-agnostic placeholders. Without standard return models, callers would still need provider-specific parsing for bars and option chains, defeating the purpose of a common feed boundary.

## What Changes

- Define normalized feed data models for market data returned by feed operations.
- Add a standard `Bar` model for one OHLCV-style price interval independent of the source provider; historical bar requests return a simple `list[Bar]`.
- Add a standard `OptionContract` model for one normalized row of an option chain, including a single call or put contract at a strike and expiration.
- Add a standard `OptionChain` model as the container for grouped `OptionContract` rows for a symbol, as-of timestamp, and optional expiration.
- Update `DataFeed` operation return annotations so current bars, historical bars, current option chains, and historical option chains return these standard models instead of provider-native or untyped data.
- Keep provider integration and real Yahoo retrieval out of scope; this change only standardizes the return contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `data-feed`: Adds provider-independent feed return data models and requires `DataFeed` operations to use them.

## Impact

- Adds normalized feed data models under the existing `feed` package.
- Changes public `DataFeed` return annotations from broad placeholders to standard project models.
- Keeps bars intentionally atomic: no separate bar-series wrapper is introduced in this change.
- Adds tests for model validation, serialization-friendly fields, and operation annotations.
- Does not add third-party provider dependencies.
- Does not implement Yahoo network retrieval.