## Why

The project needs a minimal, editable way to describe financial instrument roots such as indices, ETFs, stocks, futures, and option chains before adding market data handling. A small Pydantic-backed symbol catalog provides validation while keeping the source of truth simple JSON files instead of a database.

## What Changes

- Introduce a base symbol catalog model with three fields: `ticker`, `type`, and `contracts`.
- Represent each catalog entry as a product/root, not as every individual option strike or future data row.
- Use `contracts` to list related contract or chain identifiers whose historical data may live in separate CSV files.
- Validate supported instrument types such as `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.
- Keep underlying relationships out of scope for this initial model.

## Capabilities

### New Capabilities
- `symbol-catalog`: Defines a minimal JSON-based catalog of financial instrument products and their related contract identifiers.

### Modified Capabilities

None.

## Impact

- Adds a small domain model layer for loading and validating symbol catalog JSON with Pydantic.
- Establishes the initial data contract for future CSV-backed futures expirations, option chains, and historical data files.
- Does not introduce a database or full instrument master implementation.