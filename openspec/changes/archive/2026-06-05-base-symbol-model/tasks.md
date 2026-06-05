## 1. Project Setup

- [x] 1.1 Inspect the existing Python package layout and choose the minimal module location for the symbol code.
- [x] 1.2 Ensure Pydantic is available through the project package manager, adding it only if missing.

## 2. Symbol Model

- [x] 2.1 Define the supported instrument type enum with `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.
- [x] 2.2 Implement the Pydantic `Symbol` model with `ticker`, `type`, and `contracts`.
- [x] 2.3 Add validation so `ticker` is non-empty and `contracts` is always a list of non-empty strings.

## 3. Symbol Loading

- [x] 3.1 Implement `load_symbols` to read a JSON array of symbols from a file path.
- [x] 3.2 Ensure the loader validates all entries and fails the whole load on any invalid entry.

## 4. Tests and Examples

- [x] 4.1 Add tests for valid index, ETF, future, and option symbols.
- [x] 4.2 Add tests for unsupported instrument types and invalid contracts values.
- [x] 4.3 Add a small example `symbols.json` matching the agreed minimal structure.
- [x] 4.4 Run the focused test suite and fix any failures.