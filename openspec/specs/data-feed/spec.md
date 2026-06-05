## Purpose

Define the provider-independent async market data feed interface, capability detection behavior, normalized error semantics, and Yahoo feed adapter skeleton.

## Requirements

### Requirement: DataFeed package
The system SHALL provide a `feed` package for market data feed interfaces and provider adapters.

#### Scenario: Feed package is importable
- **WHEN** application code imports the feed package
- **THEN** the import succeeds without requiring provider-specific third-party dependencies

### Requirement: Async DataFeed operation surface
The system SHALL define a `DataFeed` base class with async methods named `get_current_bar`, `get_current_option_chain`, `get_historical_bars`, and `get_historical_option_chain` using provider-neutral parameters based on the existing `Symbol` model, date/date-time values, optional expiration, and optional interval where applicable.

#### Scenario: DataFeed exposes all feed operations
- **WHEN** a caller inspects a `DataFeed` instance
- **THEN** all four feed operation methods are present on the instance

#### Scenario: Feed operation methods are async
- **WHEN** a caller invokes any `DataFeed` feed operation method
- **THEN** the method returns an awaitable result

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