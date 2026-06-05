## 1. Project Setup

- [ ] 1.1 Inspect the existing Python package layout and choose the minimal module location for the symbol catalog code.
- [ ] 1.2 Ensure Pydantic is available through the project package manager, adding it only if missing.

## 2. Symbol Catalog Model

- [ ] 2.1 Define the supported instrument type enum with `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.
- [ ] 2.2 Implement the Pydantic symbol catalog entry model with `ticker`, `type`, and `contracts`.
- [ ] 2.3 Add validation so `ticker` is non-empty and `contracts` is always a list of non-empty strings.

## 3. Catalog Loading

- [ ] 3.1 Implement a loader that reads a JSON array of catalog entries from a file path.
- [ ] 3.2 Ensure the loader validates all entries and fails the whole load on any invalid entry.

## 4. Tests and Examples

- [ ] 4.1 Add tests for valid index, ETF, future, and option catalog entries.
- [ ] 4.2 Add tests for unsupported instrument types and invalid contracts values.
- [ ] 4.3 Add a small example JSON catalog matching the agreed minimal structure.
- [ ] 4.4 Run the focused test suite and fix any failures.