## 1. Feed Package Structure

- [ ] 1.1 Create the `feed/` package with an `__init__.py` that exports the public feed API.
- [ ] 1.2 Add module files for the `DataFeed` base interface, Yahoo adapter, and feed errors without adding third-party provider dependencies.

## 2. Feed Errors

- [ ] 2.1 Define a base `DataFeedError` exception for normalized feed failures.
- [ ] 2.2 Define `UnsupportedCapabilityError` for operations inherited from the base `DataFeed` default implementation.
- [ ] 2.3 Define request/provider-level error classes for missing provider mappings, unsupported instruments, unavailable data, authentication/entitlement failures, rate limits, network failures, timeouts, and normalization failures.

## 3. DataFeed Base Interface

- [ ] 3.1 Implement async `DataFeed.get_current_bar` with provider-neutral symbol and interval parameters and default unsupported behavior.
- [ ] 3.2 Implement async `DataFeed.get_current_option_chain` with provider-neutral symbol and expiration parameters and default unsupported behavior.
- [ ] 3.3 Implement async `DataFeed.get_historical_bars` with provider-neutral symbol, start, end, and interval parameters and default unsupported behavior.
- [ ] 3.4 Implement async `DataFeed.get_historical_option_chain` with provider-neutral symbol, as-of date, and expiration parameters and default unsupported behavior.
- [ ] 3.5 Implement `DataFeed.supports` so inherited base methods are reported unsupported and overridden feed methods are reported supported.

## 4. YahooFeed Adapter Skeleton

- [ ] 4.1 Implement `YahooFeed` in the `feed/` package as a subclass of `DataFeed`.
- [ ] 4.2 Ensure `YahooFeed` inherits unsupported behavior for any Yahoo operation not implemented in this change.
- [ ] 4.3 Export `YahooFeed` from the feed package public API.

## 5. Tests

- [ ] 5.1 Add tests that the `feed` package imports without Yahoo-specific third-party dependencies.
- [ ] 5.2 Add async tests that each base `DataFeed` operation raises `UnsupportedCapabilityError` when awaited.
- [ ] 5.3 Add tests for `supports` with inherited default methods, overridden methods, and unknown operation names.
- [ ] 5.4 Add tests that `YahooFeed` is an instance of `DataFeed` and inherits unsupported behavior for non-overridden operations.
- [ ] 5.5 Run the focused feed test suite and fix any failures.
