## Purpose

Define the provider-independent async market data feed interface, capability detection behavior, normalized error semantics, and Yahoo feed adapter skeleton.

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
The system SHALL define `Bar` as a validated model for one OHLCV market data interval with a `Symbol`, timestamp, open, high, low, close, volume, and optional interval.

#### Scenario: Valid bar is accepted
- **WHEN** a caller creates a `Bar` with a valid symbol, timestamp, OHLC prices, non-negative volume, and optional interval
- **THEN** the system accepts the bar as a provider-independent feed result

#### Scenario: Negative bar volume is rejected
- **WHEN** a caller creates a `Bar` with a negative volume
- **THEN** validation rejects the bar

### Requirement: Standard option contract model
The system SHALL define `OptionContract` as a validated model for one option contract row with underlying symbol, option symbol, expiration, strike, right, and optional normalized quote, Greek, volume, and open-interest fields.

#### Scenario: Valid option contract is accepted
- **WHEN** a caller creates an `OptionContract` with a valid underlying symbol, option symbol, expiration, strike, and right
- **THEN** the system accepts the contract as a provider-independent option row

#### Scenario: Invalid option right is rejected
- **WHEN** a caller creates an `OptionContract` with an option right other than call or put
- **THEN** validation rejects the contract

### Requirement: Standard option chain model
The system SHALL define `OptionChain` as a validated model that groups option contracts for an underlying `Symbol`, an as-of timestamp, and an optional expiration filter.

#### Scenario: Valid option chain is accepted
- **WHEN** a caller creates an `OptionChain` with a valid underlying symbol, as-of timestamp, optional expiration, and option contracts
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
The system SHALL define a `DataFeed` base class with async methods named `get_current_bar`, `get_current_option_chain`, `get_historical_bars`, and `get_historical_option_chain` using provider-neutral parameters based on the existing `Symbol` model, date/date-time values, optional expiration, and optional interval where applicable. The operation return annotations SHALL use standard feed return models: `get_current_bar` returns `Bar`, `get_current_option_chain` returns `OptionChain`, `get_historical_bars` returns `list[Bar]`, and `get_historical_option_chain` returns `OptionChain`.

#### Scenario: DataFeed exposes all feed operations
- **WHEN** a caller inspects a `DataFeed` instance
- **THEN** all four feed operation methods are present on the instance

#### Scenario: Feed operation methods are async
- **WHEN** a caller invokes any `DataFeed` feed operation method
- **THEN** the method returns an awaitable result

#### Scenario: Feed operation annotations are standardized
- **WHEN** a caller inspects the `DataFeed` operation signatures
- **THEN** each operation advertises a provider-independent standard return model

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
The system SHALL distinguish operation-level unsupported capabilities from request-level or provider-level failures.

#### Scenario: Operation is not implemented by the feed
- **WHEN** a caller invokes a feed operation that the concrete feed has not overridden
- **THEN** the system raises `UnsupportedCapabilityError`

#### Scenario: Operation exists but a request cannot be fulfilled
- **WHEN** a concrete feed operation is implemented but a specific request cannot be fulfilled because of mapping, instrument support, entitlement, unavailable data, rate limit, network, timeout, or normalization issues
- **THEN** the operation raises a normalized `DataFeedError` subtype other than `UnsupportedCapabilityError`

### Requirement: YahooFeed provider adapter
The system SHALL define a `YahooFeed` class in the `feed` package that extends `DataFeed`.

#### Scenario: YahooFeed is a DataFeed
- **WHEN** a caller creates a `YahooFeed`
- **THEN** the created object is usable anywhere a `DataFeed` is expected

#### Scenario: YahooFeed inherits unsupported operations
- **WHEN** a Yahoo operation has not been implemented by overriding the corresponding `DataFeed` method
- **THEN** YahooFeed uses the inherited unsupported-capability behavior for that operation