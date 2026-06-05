## Context

The repository currently contains a minimal Pydantic-backed symbol catalog with `Symbol`, `InstrumentType`, and `load_symbols`. The next layer is a provider-independent market data feed boundary so callers do not depend directly on Yahoo or future provider-specific APIs.

The desired first step is intentionally small: add a `feed/` package with an async `DataFeed` base interface and a `YahooFeed` subclass. This change should define the contract and capability behavior, not build a complete Yahoo integration or normalized market data model layer.

## Goals / Non-Goals

**Goals:**
- Add a `feed/` package for market data feed code.
- Define a `DataFeed` base class with async methods for current bars, current option chains, historical bars, and historical option chains.
- Let `DataFeed` provide default unsupported implementations so subclasses override only supported operations.
- Add `supports()` so callers can ask whether a feed overrides a given operation before calling it.
- Add `YahooFeed` as the first provider subclass of `DataFeed`.
- Distinguish operation-level unsupported behavior from request-level/provider-level failures in the error design.

**Non-Goals:**
- No full normalized `Bar` or `OptionChain` data models in this change.
- No real Yahoo network/API integration unless already available without adding dependencies.
- No provider routing, fallback manager, cache, persistence, or streaming websocket layer.
- No change to the existing symbol catalog schema or provider alias mapping in this change.
- No dependency installation for Yahoo libraries in this proposal.

## Decisions

### Use `DataFeed` as a base class with default unsupported methods

`DataFeed` will expose the same four async operation methods for every feed: `get_current_bar`, `get_current_option_chain`, `get_historical_bars`, and `get_historical_option_chain`. The base implementation of each method raises `UnsupportedCapabilityError`.

The initial method signatures should use the existing `Symbol` model and provider-neutral parameters: current bar requests take a symbol and optional interval, current option-chain requests take a symbol and optional expiration, historical bar requests take a symbol, start, end, and optional interval, and historical option-chain requests take a symbol, as-of date, and optional expiration. Return annotations should avoid provider-native classes until normalized feed data models are introduced.

Concrete feeds therefore do not need to write fake unsupported methods. They override only operations that are actually implemented. If Yahoo later gains historical option-chain support, `YahooFeed` can add that method override and `supports()` will reflect the new capability.

Alternative considered: separate capability interfaces for each operation. That is more explicit for static typing, but heavier for the current small four-method surface.

### Derive `supports()` from method overrides

`supports(operation)` will answer whether the concrete feed class provides an implementation different from the inherited `DataFeed` default for that operation. Direct `hasattr` is not sufficient because inherited unsupported methods still exist.

The implementation should inspect method resolution so intermediate provider base classes or mixins can still count as support when they override the base default. Callers should use `supports()` instead of duplicating introspection logic.

Alternative considered: explicit capability sets on each provider. That is easy to display, but duplicates method declarations and can drift from actual overrides.

### Keep capability support distinct from request outcome

`supports()` only means the feed implements the operation type. It does not guarantee every symbol, instrument type, entitlement, date range, or provider account can return data.

Unsupported operation errors come from inherited base methods. Provider-specific methods may raise request-level errors such as missing provider mapping, unsupported instrument, data unavailable, entitlement failure, rate limit, timeout, network failure, or normalization failure.

### Add Yahoo as the first provider subclass

`YahooFeed` will live under the new `feed/` package and extend `DataFeed`. This establishes where provider adapters belong. The class should only override operations that are implemented for Yahoo in this change; unsupported operations remain inherited from `DataFeed`.

## Risks / Trade-offs

- Method-override introspection can become subtle with decorators or complex inheritance → keep `supports()` centralized and test base, subclass, and inherited-default cases.
- A uniform four-method interface can grow too large if many feed operations are added later → revisit capability-specific interfaces if the surface expands beyond bars and option chains.
- Without normalized bar/option-chain models, return annotations may initially be broad → avoid provider-native types in public signatures and add normalized models in a future change.
- Yahoo support may be limited or unofficial depending on the eventual retrieval mechanism → keep this change focused on the interface and subclass boundary.
