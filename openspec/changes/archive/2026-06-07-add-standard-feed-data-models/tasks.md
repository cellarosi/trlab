## 1. Feed Data Model Structure

- [x] 1.1 Add a `feed/models.py` module for standard provider-independent feed return models.
- [x] 1.2 Define an `OptionRight` enum with call and put values for normalized option contracts.
- [x] 1.3 Export `Bar`, `OptionContract`, `OptionChain`, and `OptionRight` from the `feed` package public API.

## 2. Bar Model

- [x] 2.1 Implement `Bar` as a validated model with symbol, timestamp, open, high, low, close, volume, and optional interval fields.
- [x] 2.2 Use provider-independent numeric types for bar prices and validate that volume is non-negative.
- [x] 2.3 Ensure `Bar` rejects unknown fields.

## 3. Option Models

- [x] 3.1 Implement `OptionContract` with underlying symbol, option symbol, expiration, strike, right, and optional normalized quote fields.
- [x] 3.2 Add optional Greek, volume, and open-interest fields to `OptionContract` without requiring provider-specific data.
- [x] 3.3 Validate option right values and reject unknown option-contract fields.
- [x] 3.4 Implement `OptionChain` with underlying symbol, as-of timestamp, optional expiration, and a list of option contracts.
- [x] 3.5 Ensure `OptionChain` preserves normalized call and put contract rows in its contracts collection.

## 4. DataFeed Return Contract

- [x] 4.1 Update `DataFeed.get_current_bar` to return the standard `Bar` model annotation.
- [x] 4.2 Update `DataFeed.get_historical_bars` to return `list[Bar]`.
- [x] 4.3 Update `DataFeed.get_current_option_chain` and `DataFeed.get_historical_option_chain` to return `OptionChain`.
- [x] 4.4 Preserve existing default unsupported behavior and `supports()` capability detection.

## 5. Tests

- [x] 5.1 Add tests, with comments/docstrings explaining each test, for importing feed models from the public API without provider-specific dependencies.
- [x] 5.2 Add tests, with comments/docstrings, for valid `Bar` creation, negative volume rejection, and unknown field rejection.
- [x] 5.3 Add tests, with comments/docstrings, for valid `OptionContract` creation and invalid option right rejection.
- [x] 5.4 Add tests, with comments/docstrings, for `OptionChain` creation and contract preservation.
- [x] 5.5 Add tests, with comments/docstrings, for standardized `DataFeed` operation return annotations.
- [x] 5.6 Run the focused feed test suite and full test discovery, then fix any failures.