## ADDED Requirements

### Requirement: TiingoFeed provider adapter
The system SHALL define a `TiingoFeed` class in the `feed` package that extends `DataFeed` and implements only Tiingo-backed `get_current_bar` and `get_historical_bars` operations while leaving option-chain operations unsupported.

#### Scenario: TiingoFeed is a DataFeed
- **WHEN** a caller creates a `TiingoFeed`
- **THEN** the created object is usable anywhere a `DataFeed` is expected

#### Scenario: TiingoFeed supports implemented operations
- **WHEN** a caller checks `supports` for `get_current_bar` or `get_historical_bars` on a `TiingoFeed`
- **THEN** `supports` reports those operations as supported

#### Scenario: TiingoFeed option chains remain unsupported
- **WHEN** a caller checks `supports` for `get_current_option_chain` or `get_historical_option_chain` on a `TiingoFeed`
- **THEN** `supports` reports those operations as unsupported

#### Scenario: TiingoFeed unsupported option-chain calls raise unsupported
- **WHEN** a caller awaits a TiingoFeed option-chain operation
- **THEN** TiingoFeed uses the inherited unsupported-capability behavior for that operation

### Requirement: Tiingo token handling
The system SHALL require callers to pass a Tiingo API token explicitly when constructing `TiingoFeed` without hard-coding secrets in source code.

#### Scenario: Explicit Tiingo token is used
- **WHEN** a caller creates `TiingoFeed` with an explicit API token and invokes a supported operation
- **THEN** Tiingo requests authenticate with that token

#### Scenario: Empty Tiingo token raises authentication error
- **WHEN** a caller creates `TiingoFeed` with an empty or blank API token
- **THEN** construction raises `DataFeedAuthenticationError`

#### Scenario: Feed import does not require Tiingo token
- **WHEN** application code imports `feed` without creating or invoking `TiingoFeed`
- **THEN** the import succeeds without a Tiingo token

### Requirement: TiingoFeed current bar retrieval
The system SHALL implement `TiingoFeed.get_current_bar` using Tiingo end-of-day data and return the latest available Tiingo bar as a standard `Bar` model.

#### Scenario: Current Tiingo bar returns standard Bar
- **WHEN** a caller awaits `TiingoFeed.get_current_bar` for a provider-ready ticker with Tiingo end-of-day data available
- **THEN** the system returns a `Bar` containing the requested ticker, a timestamp, OHLC prices, non-negative volume, and the requested interval when provided

#### Scenario: Current Tiingo bar uses latest available end-of-day row
- **WHEN** Tiingo returns multiple end-of-day rows for the current-bar request
- **THEN** the system returns the newest row by Tiingo date

#### Scenario: Current Tiingo bar handles missing data
- **WHEN** Tiingo does not return enough current bar fields for the requested ticker
- **THEN** the system raises a normalized `DataUnavailableError`

### Requirement: TiingoFeed historical bar retrieval
The system SHALL implement `TiingoFeed.get_historical_bars` using Tiingo end-of-day historical prices and return a list of standard `Bar` models.

#### Scenario: Historical Tiingo bars return standard Bar list
- **WHEN** a caller awaits `TiingoFeed.get_historical_bars` for a provider-ready ticker, date range, and optional interval with Tiingo data available
- **THEN** the system returns `list[Bar]` in provider-neutral format for each returned historical row

#### Scenario: Historical Tiingo bars request date bounds
- **WHEN** a caller passes start and end dates to `TiingoFeed.get_historical_bars`
- **THEN** the Tiingo request includes the corresponding `startDate` and `endDate` parameters

#### Scenario: Empty Tiingo historical bars are unavailable
- **WHEN** Tiingo returns no historical rows for the requested ticker and range
- **THEN** the system raises a normalized `DataUnavailableError`

### Requirement: Tiingo provider error normalization
The system SHALL convert Tiingo request, authentication, rate-limit, unavailable-data, and payload-normalization failures into normalized `DataFeedError` subtypes.

#### Scenario: Tiingo authentication failure is normalized
- **WHEN** Tiingo rejects a request because the token is invalid or unauthorized
- **THEN** the system raises `DataFeedAuthenticationError` or `EntitlementError`

#### Scenario: Tiingo rate limit is normalized
- **WHEN** Tiingo rejects a request because of rate limiting
- **THEN** the system raises `RateLimitError`

#### Scenario: Tiingo network failure is normalized
- **WHEN** a Tiingo request fails because of network or timeout conditions
- **THEN** the system raises `NetworkError` or `DataFeedTimeoutError`

#### Scenario: Tiingo payload normalization failure is normalized
- **WHEN** Tiingo returns malformed or incomplete bar payloads
- **THEN** the system raises `NormalizationError` or `DataUnavailableError`

### Requirement: Tiingo live smoke-test script
The system SHALL provide a repository script for manual live Tiingo checks that accepts a Tiingo token as a command-line argument and passes it to `TiingoFeed` while exercising supported operations.

#### Scenario: Tiingo script exercises supported operations
- **WHEN** a developer runs the Tiingo live smoke-test script with a valid Tiingo token argument
- **THEN** the script fetches a current bar and a short historical bar range and prints concise non-secret results

#### Scenario: Tiingo script avoids exposing token
- **WHEN** the Tiingo live smoke-test script reports progress or errors
- **THEN** it does not print the configured Tiingo token