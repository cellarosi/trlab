## Purpose

Define the provider-independent async market data feed interface, standard feed return models, capability detection behavior, normalized error semantics, and the Yahoo feed adapter.

## Requirements

### Requirement: DataFeed package
The system SHALL provide a `feed` package for market data feed interfaces and provider adapters.

#### Scenario: Feed package is importable
- **WHEN** application code imports the feed package
- **THEN** the import succeeds without requiring provider-specific third-party dependencies

### Requirement: Standard feed return models
The system SHALL define provider-independent feed return models named `Bar`, `OptionContract`, and `OptionChain` in the `feed` package.

#### Scenario: Feed models are importable from the public API
- **WHEN** application code imports `Bar`, `OptionContract`, and `OptionChain` from `feed`
- **THEN** the import succeeds without requiring provider-specific third-party dependencies

#### Scenario: Feed models reject unknown fields
- **WHEN** a caller creates a standard feed return model with fields outside the model schema
- **THEN** validation rejects the unknown fields

### Requirement: Standard Bar model
The system SHALL define `Bar` as a validated model for one OHLCV market data interval with a ticker string, timestamp, open, high, low, close, volume, and optional interval.

#### Scenario: Valid bar is accepted
- **WHEN** a caller creates a `Bar` with a valid ticker, timestamp, OHLC prices, non-negative volume, and optional interval
- **THEN** the system accepts the bar as a provider-independent feed result

#### Scenario: Negative bar volume is rejected
- **WHEN** a caller creates a `Bar` with a negative volume
- **THEN** validation rejects the bar

### Requirement: Standard option contract model
The system SHALL define `OptionContract` as a validated model for one option contract row with underlying ticker, option ticker, expiration, strike, right, and optional normalized quote, Greek, volume, and open-interest fields.

#### Scenario: Valid option contract is accepted
- **WHEN** a caller creates an `OptionContract` with a valid underlying ticker, option ticker, expiration, strike, and right
- **THEN** the system accepts the contract as a provider-independent option row

#### Scenario: Invalid option right is rejected
- **WHEN** a caller creates an `OptionContract` with an option right other than call or put
- **THEN** validation rejects the contract

### Requirement: Standard option chain model
The system SHALL define `OptionChain` as a validated model that groups option contracts for an underlying ticker, an as-of timestamp, and an optional expiration filter.

#### Scenario: Valid option chain is accepted
- **WHEN** a caller creates an `OptionChain` with a valid underlying ticker, as-of timestamp, optional expiration, and option contracts
- **THEN** the system accepts the chain as a provider-independent feed result

#### Scenario: Chain contracts preserve normalized rows
- **WHEN** an `OptionChain` contains multiple call and put `OptionContract` rows
- **THEN** the chain preserves those rows in its `contracts` collection

### Requirement: Feed operation return annotations use standard models
The system SHALL annotate `DataFeed` operation return types with standard feed models instead of provider-native or untyped values.

#### Scenario: Current bar returns Bar
- **WHEN** a caller inspects `DataFeed.get_current_bar`
- **THEN** the return annotation is the standard `Bar` model

#### Scenario: Historical bars return a list of Bar
- **WHEN** a caller inspects `DataFeed.get_historical_bars`
- **THEN** the return annotation is a list of standard `Bar` models

#### Scenario: Option-chain operations return OptionChain
- **WHEN** a caller inspects `DataFeed.get_current_option_chain` and `DataFeed.get_historical_option_chain`
- **THEN** each return annotation is the standard `OptionChain` model

### Requirement: Async DataFeed operation surface
The system SHALL define a `DataFeed` base class with async methods named `get_current_bar`, `get_current_option_chain`, `get_historical_bars`, and `get_historical_option_chain` using provider-ready ticker string parameters, date/date-time values, optional expiration, and optional interval where applicable. The operation return annotations SHALL use standard feed return models: `get_current_bar` returns `Bar`, `get_current_option_chain` returns `OptionChain`, `get_historical_bars` returns `list[Bar]`, and `get_historical_option_chain` returns `OptionChain`.

#### Scenario: DataFeed exposes all feed operations
- **WHEN** a caller inspects a `DataFeed` instance
- **THEN** all four feed operation methods are present on the instance

#### Scenario: Feed operation methods are async
- **WHEN** a caller invokes any `DataFeed` feed operation method
- **THEN** the method returns an awaitable result

#### Scenario: Feed operation annotations are standardized
- **WHEN** a caller inspects the `DataFeed` operation signatures
- **THEN** each operation advertises a provider-independent standard return model

#### Scenario: Feed operations use ticker strings
- **WHEN** a caller inspects the `DataFeed` operation signatures
- **THEN** each operation accepts a ticker string instead of a `Symbol` object

### Requirement: Default unsupported operation behavior
The system SHALL make each base `DataFeed` feed operation raise a normalized unsupported-capability error unless a subclass overrides that operation.

#### Scenario: Base historical option-chain operation is unsupported
- **WHEN** a caller awaits `DataFeed.get_historical_option_chain`
- **THEN** the system raises `UnsupportedCapabilityError`

#### Scenario: Subclass does not need fake unsupported methods
- **WHEN** a concrete feed does not support a feed operation
- **THEN** the concrete feed can inherit the base implementation for that operation

### Requirement: Capability detection
The system SHALL provide `DataFeed.supports` so callers can check whether a concrete feed overrides a supported feed operation before invoking it.

#### Scenario: Inherited base operation is not supported
- **WHEN** a concrete feed inherits a feed operation directly from `DataFeed`
- **THEN** `supports` reports that operation as unsupported

#### Scenario: Overridden feed operation is supported
- **WHEN** a concrete feed overrides a feed operation from `DataFeed`
- **THEN** `supports` reports that operation as supported

#### Scenario: Unknown operation is not supported
- **WHEN** a caller asks `supports` about an unknown operation name
- **THEN** `supports` reports the operation as unsupported

### Requirement: Feed error semantics
The system SHALL distinguish operation-level unsupported capabilities from request-level or provider-level failures, including failures from Yahoo-backed operations.

#### Scenario: Operation is not implemented by the feed
- **WHEN** a caller invokes a feed operation that the concrete feed has not overridden
- **THEN** the system raises `UnsupportedCapabilityError`

#### Scenario: Operation exists but a request cannot be fulfilled
- **WHEN** a concrete feed operation is implemented but a specific request cannot be fulfilled because of mapping, instrument support, entitlement, unavailable data, rate limit, network, timeout, or normalization issues
- **THEN** the operation raises a normalized `DataFeedError` subtype other than `UnsupportedCapabilityError`

#### Scenario: Yahoo provider failure is normalized
- **WHEN** a Yahoo-backed operation encounters a provider client error, unrecognized ticker, missing data, or a normalization failure
- **THEN** the system raises an appropriate normalized `DataFeedError` subtype instead of returning provider-native errors or payloads

### Requirement: YahooFeed current bar retrieval
The system SHALL implement `YahooFeed.get_current_bar` for Yahoo delayed/current market data and return a standard `Bar` model.

#### Scenario: Current Yahoo bar returns standard Bar
- **WHEN** a caller awaits `YahooFeed.get_current_bar` for a provider-ready ticker with Yahoo data available
- **THEN** the system returns a `Bar` containing the requested ticker, a timestamp, OHLC prices, non-negative volume, and the requested interval when provided

#### Scenario: Current Yahoo bar handles missing data
- **WHEN** Yahoo does not return enough current bar fields for the requested ticker
- **THEN** the system raises a normalized `DataUnavailableError`

### Requirement: YahooFeed historical bar retrieval
The system SHALL implement `YahooFeed.get_historical_bars` for Yahoo historical OHLCV data and return a list of standard `Bar` models.

#### Scenario: Historical Yahoo bars return standard Bar list
- **WHEN** a caller awaits `YahooFeed.get_historical_bars` for a provider-ready ticker, date range, and optional interval with Yahoo data available
- **THEN** the system returns `list[Bar]` in provider-neutral format for each returned historical row

#### Scenario: Empty Yahoo historical bars are unavailable
- **WHEN** Yahoo returns no historical rows for the requested ticker and range
- **THEN** the system raises a normalized `DataUnavailableError`

### Requirement: YahooFeed current option-chain retrieval
The system SHALL implement `YahooFeed.get_current_option_chain` for Yahoo current option chains and return a standard `OptionChain` model containing normalized call and put contracts.

#### Scenario: Current Yahoo option chain returns standard OptionChain
- **WHEN** a caller awaits `YahooFeed.get_current_option_chain` for a provider-ready underlying ticker and optional expiration with Yahoo option data available
- **THEN** the system returns an `OptionChain` with the requested underlying ticker, an as-of timestamp, the selected expiration when provided, and normalized `OptionContract` rows

#### Scenario: Yahoo option chain preserves calls and puts
- **WHEN** Yahoo returns call and put rows for the requested option chain
- **THEN** the system preserves both call and put rows in the returned `OptionChain.contracts` collection with the correct `OptionRight`

#### Scenario: Missing Yahoo option-chain data is unavailable
- **WHEN** Yahoo returns no option-chain rows for the requested ticker or expiration
- **THEN** the system raises a normalized `DataUnavailableError`

### Requirement: YahooFeed lazy provider dependency
The system SHALL avoid importing or requiring Yahoo-specific provider dependencies when application code only imports the public `feed` package.

#### Scenario: Feed import stays provider independent
- **WHEN** application code imports `feed` without invoking Yahoo-backed operations
- **THEN** the import succeeds without loading Yahoo-specific third-party modules

#### Scenario: Missing Yahoo dependency fails at operation time
- **WHEN** a caller invokes a Yahoo-backed operation and the Yahoo provider client dependency is unavailable
- **THEN** the system raises a normalized `DataFeedError` subtype instead of an import error leaking to the caller

### Requirement: YahooFeed provider adapter
The system SHALL define a `YahooFeed` class in the `feed` package that extends `DataFeed` and implements the Yahoo-supported operations `get_current_bar`, `get_historical_bars`, and `get_current_option_chain` while leaving `get_historical_option_chain` unsupported.

#### Scenario: YahooFeed is a DataFeed
- **WHEN** a caller creates a `YahooFeed`
- **THEN** the created object is usable anywhere a `DataFeed` is expected

#### Scenario: YahooFeed supports implemented operations
- **WHEN** a caller checks `supports` for `get_current_bar`, `get_historical_bars`, or `get_current_option_chain` on a `YahooFeed`
- **THEN** `supports` reports those operations as supported

#### Scenario: YahooFeed historical option chain remains unsupported
- **WHEN** a caller checks `supports` for `get_historical_option_chain` on a `YahooFeed`
- **THEN** `supports` reports the operation as unsupported

#### Scenario: YahooFeed historical option chain raises unsupported
- **WHEN** a caller awaits `YahooFeed.get_historical_option_chain`
- **THEN** YahooFeed uses the inherited unsupported-capability behavior for that operation