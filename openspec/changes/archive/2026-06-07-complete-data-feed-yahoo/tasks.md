## 1. Yahoo Adapter Setup

- [x] 1.1 Add the Yahoo provider client dependency through the project package manager if it is not already available.
- [x] 1.2 Keep `YahooFeed` using lazy `yfinance.Ticker` construction without adding a production client-factory abstraction.
- [x] 1.3 Implement lazy Yahoo client loading so importing `feed` does not import Yahoo-specific third-party modules.
- [x] 1.4 Update `DataFeed` method signatures to accept `ticker: str` instead of `Symbol` parameters.
- [x] 1.5 Update standard feed return models to use ticker string fields instead of `Symbol` fields.
- [x] 1.6 Validate that Yahoo-backed methods receive a non-empty provider-ready ticker string without performing provider mapping inside `YahooFeed`.

## 2. Bar Retrieval Implementation

- [x] 2.1 Implement `YahooFeed.get_current_bar` and ensure `supports("get_current_bar")` reports true.
- [x] 2.2 Normalize Yahoo current quote/history data into the standard `Bar` model with ticker, timestamp, OHLC, non-negative volume, and optional interval.
- [x] 2.3 Raise `DataUnavailableError` when Yahoo current bar data is empty or missing required fields.
- [x] 2.4 Implement `YahooFeed.get_historical_bars` and ensure `supports("get_historical_bars")` reports true.
- [x] 2.5 Normalize Yahoo historical OHLCV rows into `list[Bar]` for the requested provider-ready ticker, date/datetime range, and interval.
- [x] 2.6 Raise `DataUnavailableError` when Yahoo historical bar data is empty.

## 3. Option Chain Implementation

- [x] 3.1 Implement `YahooFeed.get_current_option_chain` and ensure `supports("get_current_option_chain")` reports true.
- [x] 3.2 Treat the option-chain ticker as an already provider-ready underlying ticker and select the requested Yahoo expiration when provided.
- [x] 3.3 Normalize Yahoo call rows into `OptionContract` values with `OptionRight.CALL`.
- [x] 3.4 Normalize Yahoo put rows into `OptionContract` values with `OptionRight.PUT`.
- [x] 3.5 Return a standard `OptionChain` preserving all normalized call and put contracts.
- [x] 3.6 Raise `DataUnavailableError` when Yahoo option-chain data is empty or unavailable.

## 4. Error Semantics and Unsupported Behavior

- [x] 4.1 Map Yahoo provider/client exceptions into normalized `DataFeedError` subtypes without leaking provider-native exceptions.
- [x] 4.2 Map normalization failures into `NormalizationError` with useful context.
- [x] 4.3 Preserve inherited `get_historical_option_chain` behavior so `supports("get_historical_option_chain")` remains false.
- [x] 4.4 Keep the existing public `feed` import behavior independent from eager Yahoo dependency loading.

## 5. Tests and Validation

- [x] 5.1 Add fake-client tests for current Yahoo bar success and missing-data failure.
- [x] 5.2 Add fake-client tests for historical Yahoo bars success and empty-result failure.
- [x] 5.3 Add fake-client tests for current Yahoo option-chain success, expiration handling, call/put preservation, and empty-result failure.
- [x] 5.4 Add tests for Yahoo `supports()` behavior across the three implemented operations and unsupported historical option chains.
- [x] 5.5 Add tests proving `import feed` does not eagerly load Yahoo-specific third-party modules.
- [x] 5.6 Add tests for missing Yahoo dependency and provider/normalization error mapping.
- [x] 5.7 Run focused feed tests and full unittest discovery, then fix any failures.