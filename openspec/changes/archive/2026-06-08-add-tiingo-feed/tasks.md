## 1. Public API and Adapter Skeleton

- [x] 1.1 Add `feed/tiingo.py` with a `TiingoFeed` class extending `DataFeed`.
- [x] 1.2 Export `TiingoFeed` from `feed/__init__.py` and include it in `__all__`.
- [x] 1.3 Confirm `TiingoFeed.supports()` reports current/historical bars as supported and option-chain methods as unsupported.

## 2. Token and HTTP Request Handling

- [x] 2.1 Implement Tiingo token handling through a required explicit constructor argument without requiring a token at import time.
- [x] 2.2 Raise `DataFeedAuthenticationError` when `TiingoFeed` is constructed with an empty token.
- [x] 2.3 Implement authenticated Tiingo REST requests using the `Authorization: Token ...` header without logging or exposing the token.
- [x] 2.4 Build Tiingo EOD request URLs for `/tiingo/daily/{ticker}/prices` with `startDate`, `endDate`, and `resampleFreq` query parameters.

## 3. Bar Retrieval and Normalization

- [x] 3.1 Implement `get_historical_bars` to fetch Tiingo EOD rows for a ticker/date range and return `list[Bar]`.
- [x] 3.2 Implement `get_current_bar` to fetch and return the newest available Tiingo EOD row as a `Bar`.
- [x] 3.3 Normalize Tiingo `date`, `open`, `high`, `low`, `close`, and `volume` fields into standard `Bar` fields.
- [x] 3.4 Preserve the requested interval on returned `Bar` models and use Tiingo `daily` resampling when no interval is provided.
- [x] 3.5 Raise `DataUnavailableError` or `NormalizationError` for empty, malformed, or incomplete Tiingo payloads.

## 4. Error Mapping

- [x] 4.1 Map Tiingo 401/403 responses to `DataFeedAuthenticationError` or `EntitlementError`.
- [x] 4.2 Map Tiingo 404/empty-data responses to `DataUnavailableError`.
- [x] 4.3 Map Tiingo 429 responses to `RateLimitError`.
- [x] 4.4 Map network failures and timeouts to `NetworkError` and `DataFeedTimeoutError`.

## 5. Tests

- [x] 5.1 Add unit tests proving `import feed` does not require a Tiingo token or eagerly perform provider work.
- [x] 5.2 Add unit tests for explicit token handling and blank-token rejection without exposing token values in output.
- [x] 5.3 Add fake-response tests for successful current Tiingo bar normalization.
- [x] 5.4 Add fake-response tests for successful historical Tiingo bar normalization and date/query parameter handling.
- [x] 5.5 Add tests for empty, malformed, and missing-field Tiingo payload behavior.
- [x] 5.6 Add tests for Tiingo HTTP status and network error normalization.
- [x] 5.7 Add tests for `TiingoFeed.supports()` and inherited unsupported option-chain behavior.

## 6. Live Smoke Script and Verification

- [x] 6.1 Add `scripts/test_tiingo_download.py` that accepts a Tiingo token argument, passes it to `TiingoFeed`, and exercises current and historical bar calls.
- [x] 6.2 Ensure the live smoke script prints concise ticker/bar results and never prints the token.
- [x] 6.3 Run the focused feed unit tests and fix any failures.
- [x] 6.4 Document the manual live script command and token argument in the script header.