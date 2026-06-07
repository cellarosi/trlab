## 1. Feed Data Model Structure

- [ ] 1.1 Add a `feed/models.py` module for standard provider-independent feed return models.
- [ ] 1.2 Define an `OptionRight` enum with call and put values for normalized option contracts.
- [ ] 1.3 Export `Bar`, `OptionContract`, `OptionChain`, and `OptionRight` from the `feed` package public API.

## 2. Bar Model

- [ ] 2.1 Implement `Bar` as a validated model with symbol, timestamp, open, high, low, close, volume, and optional interval fields.
- [ ] 2.2 Use provider-independent numeric types for bar prices and validate that volume is non-negative.
- [ ] 2.3 Ensure `Bar` rejects unknown fields.

## 3. Option Models

- [ ] 3.1 Implement `OptionContract` with underlying symbol, option symbol, expiration, strike, right, and optional normalized quote fields.
- [ ] 3.2 Add optional Greek, volume, and open-interest fields to `OptionContract` without requiring provider-specific data.
- [ ] 3.3 Validate option right values and reject unknown option-contract fields.
- [ ] 3.4 Implement `OptionChain` with underlying symbol, as-of timestamp, optional expiration, and a list of option contracts.
- [ ] 3.5 Ensure `OptionChain` preserves normalized call and put contract rows in its contracts collection.

## 4. DataFeed Return Contract

- [ ] 4.1 Update `DataFeed.get_current_bar` to return the standard `Bar` model annotation.
- [ ] 4.2 Update `DataFeed.get_historical_bars` to return `list[Bar]`.
- [ ] 4.3 Update `DataFeed.get_current_option_chain` and `DataFeed.get_historical_option_chain` to return `OptionChain`.
- [ ] 4.4 Preserve existing default unsupported behavior and `supports()` capability detection.

## 5. Tests

- [ ] 5.1 Add tests, with comments/docstrings explaining each test, for importing feed models from the public API without provider-specific dependencies.
- [ ] 5.2 Add tests, with comments/docstrings, for valid `Bar` creation, negative volume rejection, and unknown field rejection.
- [ ] 5.3 Add tests, with comments/docstrings, for valid `OptionContract` creation and invalid option right rejection.
- [ ] 5.4 Add tests, with comments/docstrings, for `OptionChain` creation and contract preservation.
- [ ] 5.5 Add tests, with comments/docstrings, for standardized `DataFeed` operation return annotations.
- [ ] 5.6 Run the focused feed test suite and full test discovery, then fix any failures.