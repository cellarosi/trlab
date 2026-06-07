## Context

The archived `add-data-feed-interface` change introduced a provider-independent async `DataFeed` interface with broad return annotations. That established operation names and capability behavior, but it intentionally deferred normalized market data models. The next step is to make the feed boundary useful to callers by ensuring bars and option chains are returned in project-defined formats, not provider-native dictionaries or objects.

The repository already uses Pydantic for validated domain models in `symbols.models`, so feed return models can use the same dependency without adding new packages.

## Goals / Non-Goals

**Goals:**
- Define standard feed return models for bars and option chains under the existing `feed` package.
- Keep the models provider-independent and serialization-friendly.
- Update `DataFeed` method annotations so each operation advertises a concrete standard return type.
- Export the standard models from the `feed` package public API.
- Add tests for model validation and `DataFeed` return annotations.

**Non-Goals:**
- No real Yahoo retrieval implementation.
- No provider-specific normalization logic beyond defining the target models.
- No persistence, caching, streaming, or aggregation behavior.
- No exhaustive market data schema for every possible provider field.

## Decisions

### Use Pydantic models for feed return data

`Bar`, `OptionContract`, and `OptionChain` will be Pydantic models. This matches the existing `Symbol` model approach and provides runtime validation for provider adapters before returning data to callers.

Alternative considered: plain dataclasses. Dataclasses are lighter, but they would require separate validation and would be inconsistent with the existing symbol catalog model style.

### Keep bars simple and required

`Bar` will represent one OHLCV interval with `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, and optional `interval`. Price fields should use `Decimal` to avoid forcing floating-point representation into the public contract. Volume should be numeric and non-negative.

Historical bar data will not introduce a separate wrapper model in this change. It will be represented as `list[Bar]`, where each `Bar` is one atomic row/candle in the time series.

Alternative considered: provider-specific bar payload passthrough. That keeps adapters simple but pushes provider normalization into every caller.

### Model option chains as grouped contracts

`OptionContract` will represent one option-chain row with normalized fields for underlying symbol, option symbol, expiration, strike, right, and optional quote/Greek/open-interest fields. In other words, one `OptionContract` is one call or put contract at a specific strike and expiration. `OptionChain` will group those rows by underlying symbol, as-of timestamp, and optional expiration filter.

Alternative considered: separate call and put lists. A single contract list with an explicit right is simpler for filtering, serialization, and provider normalization.

### Update return annotations without changing unsupported behavior

Base `DataFeed` methods will continue to raise `UnsupportedCapabilityError` by default. Only their return annotations change: current bar returns `Bar`, historical bars returns `list[Bar]`, and option-chain operations return `OptionChain`.

Alternative considered: leave annotations broad until Yahoo retrieval exists. That delays the standard contract and makes future adapter work more likely to leak provider-native data.

## Risks / Trade-offs

- Model fields may be too narrow for future providers → keep optional market data fields for option contracts and extend models in later changes as needed.
- Decimal values may require conversion from provider floats → provider adapters should normalize before returning standard models.
- Validation rules could reject legitimate edge cases → start with conservative non-negative numeric validation and adjust with tests when new providers require it.