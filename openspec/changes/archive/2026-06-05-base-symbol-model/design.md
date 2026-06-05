## Context

The project is at an early stage and needs a lightweight representation of financial instrument roots before introducing historical market data, futures expirations, or option chains. The desired source of truth is a manually editable JSON catalog, with related CSV files added later for per-contract or per-chain data.

The initial catalog intentionally avoids a database, filesystem-derived hierarchy, and full instrument master semantics. It captures only the minimal information needed to know which products exist and which contract identifiers may have external CSV data.

## Goals / Non-Goals

**Goals:**
- Define a Pydantic `Symbol` model in `symbols.models`.
- Support entries with `ticker`, `type`, and `contracts`.
- Validate a small fixed set of instrument types: `INDEX`, `ETF`, `STOCK`, `FUTURE`, and `OPTION`.
- Provide `load_symbols` for loading a JSON array of symbols from a file path.
- Keep option strikes, option rights, futures expiry details, and historical data outside the base catalog.
- Allow `contracts` to reference future CSV-backed data files by name.

**Non-Goals:**
- No database schema or persistence layer.
- No full security master or global symbol identity system.
- No explicit underlying relationship in this change.
- No option-chain row model, pricing model, Greeks, or market data loader.
- No dependency installation in the proposal itself; implementation should add Pydantic through the project package manager if it is not already available.

## Decisions

### Use JSON as the catalog source of truth

The catalog will be represented as a JSON array of symbols. This is easier to edit manually than a single wide CSV while remaining simple to load, diff, and validate.

Alternative considered: CSV. CSV is compact, but nested lists like `contracts` become awkward and require custom parsing conventions.

### Use Pydantic for validation

Each symbol will be represented by the Pydantic `Symbol` model. This gives runtime validation for required fields, supported instrument types, and `contracts` list shape without building a database layer.

Alternative considered: dataclasses only. Dataclasses are lighter but would require separate validation code.

### Keep `contracts` generic

The `contracts` field will be a list of strings. For an index it can be empty; for an ETF or stock it can contain the ticker itself; for futures it can contain contract symbols such as `ESZ5`; for options it can contain chain or expiry identifiers such as `SPY20260320`.

Alternative considered: separate `expirations`, `chains`, and `contracts` fields. Separate fields are more explicit but add complexity before the downstream file layout is settled.

### Exclude `underlying` for now

The initial model will not include an `underlying` field. The current goal is to establish a minimal catalog and validation model; relationship modeling can be added later if it becomes necessary.

Alternative considered: include `underlying` immediately. This improves graph traversal but reintroduces relationship modeling that the current simplified design intentionally postpones.

## Risks / Trade-offs

- Ambiguous tickers across instrument types → Use `ticker` plus `type` together when looking up entries, not `ticker` alone.
- Missing relationship data → Add an `underlying` or relationship field in a later change if lookup/navigation needs require it.
- Generic `contracts` semantics → Document that `contracts` contains external CSV identifiers, not necessarily tradable contracts in every case.
- Pydantic dependency may be absent → Add it with the package manager during implementation if needed.