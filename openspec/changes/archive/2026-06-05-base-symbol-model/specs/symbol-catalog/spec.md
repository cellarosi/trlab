## ADDED Requirements

### Requirement: Symbol model
The system SHALL define a validated `Symbol` model with `ticker`, `type`, and `contracts` fields.

#### Scenario: Valid index entry
- **WHEN** a symbol contains ticker `SPX`, type `INDEX`, and an empty contracts list
- **THEN** the system accepts the entry as valid

#### Scenario: Valid future product entry
- **WHEN** a symbol contains ticker `ES`, type `FUTURE`, and contracts `ESZ5` and `ESH6`
- **THEN** the system accepts the entry as a future product with related contract identifiers

### Requirement: Supported instrument types
The system SHALL restrict symbol types to `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.

#### Scenario: Unsupported type is rejected
- **WHEN** a symbol contains an instrument type outside the supported set
- **THEN** the system rejects the entry during validation

### Requirement: Contract identifiers are catalog references
The system SHALL treat `contracts` values as string identifiers for related CSV-backed data, not as fully expanded instrument records.

#### Scenario: Option entry references chain identifiers
- **WHEN** an option symbol contains contracts such as `SPY20260320`
- **THEN** the system preserves those values as external chain or expiry identifiers

### Requirement: Symbol loading
The system SHALL load a JSON array of symbols with `load_symbols` and validate every entry before returning the symbols.

#### Scenario: Invalid symbols file fails loading
- **WHEN** any entry in the JSON symbols file fails validation
- **THEN** the system reports a validation failure instead of returning a partially valid list