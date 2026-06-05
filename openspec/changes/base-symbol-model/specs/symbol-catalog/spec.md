## ADDED Requirements

### Requirement: Symbol catalog entry model
The system SHALL define a validated symbol catalog entry with `ticker`, `type`, and `contracts` fields.

#### Scenario: Valid index entry
- **WHEN** a catalog entry contains ticker `SPX`, type `INDEX`, and an empty contracts list
- **THEN** the system accepts the entry as valid

#### Scenario: Valid future product entry
- **WHEN** a catalog entry contains ticker `ES`, type `FUTURE`, and contracts `ESZ5` and `ESH6`
- **THEN** the system accepts the entry as a future product with related contract identifiers

### Requirement: Supported instrument types
The system SHALL restrict symbol catalog entry types to `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.

#### Scenario: Unsupported type is rejected
- **WHEN** a catalog entry contains an instrument type outside the supported set
- **THEN** the system rejects the entry during validation

### Requirement: Contract identifiers are catalog references
The system SHALL treat `contracts` values as string identifiers for related CSV-backed data, not as fully expanded instrument records.

#### Scenario: Option entry references chain identifiers
- **WHEN** an option catalog entry contains contracts such as `SPY20260320`
- **THEN** the system preserves those values as external chain or expiry identifiers

### Requirement: Catalog loading
The system SHALL load a JSON array of symbol catalog entries and validate every entry before returning the catalog.

#### Scenario: Invalid catalog fails loading
- **WHEN** any entry in the JSON catalog fails validation
- **THEN** the system reports a validation failure instead of returning a partially valid catalog