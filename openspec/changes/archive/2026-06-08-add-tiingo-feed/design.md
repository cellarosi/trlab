## Context

The project already defines a provider-independent async `DataFeed` surface, normalized `Bar` models, feed-layer exceptions, and a `YahooFeed` adapter. Tiingo will be added as a second provider adapter focused on end-of-day equities/ETF bar data. The Tiingo API requires an API token and exposes end-of-day prices through REST endpoints such as `/tiingo/daily/{ticker}/prices` with `startDate`, `endDate`, and `resampleFreq` query parameters.

## Goals / Non-Goals

**Goals:**

- Provide `TiingoFeed` as a public `feed` adapter that implements `get_current_bar` and `get_historical_bars` only.
- Keep the public feed package importable without a Tiingo token or Tiingo-specific third-party package.
- Support secure token configuration through an explicit constructor argument only.
- Normalize Tiingo EOD payloads into existing `Bar` models and existing feed exception types.
- Add a manual live smoke-test script for token-backed Tiingo checks.

**Non-Goals:**

- Implement Tiingo options, crypto, forex, websocket, fundamentals, or intraday/IEX behavior.
- Store or scaffold a real Tiingo token in source control.
- Replace or modify the existing Yahoo adapter behavior.

## Decisions

- **Use the standard library HTTP client first.** Implement Tiingo REST calls with `urllib.request`/`urllib.parse` unless implementation proves a dependency is needed. This avoids a package-manager change and keeps provider code lightweight. Alternative considered: adding `requests` or the official Tiingo client; rejected initially because the required calls are simple and dependency changes are avoidable.
- **Token resolution is caller-owned and explicit.** `TiingoFeed` requires a non-empty `api_token` constructor argument and never performs credential lookup itself. The code that chooses and constructs the feed is responsible for retrieving the token from configuration, a secret manager, a CLI argument, or another source. Alternative considered: adapter-level fallback lookup; rejected because provider credential lookup should stay outside the feed adapter.
- **Map Tiingo EOD rows to unadjusted OHLCV by default.** Use `open`, `high`, `low`, `close`, and `volume` fields for the standard `Bar`; preserve the requested feed interval string on the model. Alternative considered: adjusted prices; rejected because the existing `Bar` schema has no adjusted/unadjusted indicator.
- **Treat current bar as latest available EOD bar.** `get_current_bar` returns the newest Tiingo EOD row for the ticker, rather than promising intraday real-time data. Alternative considered: Tiingo IEX latest prices; rejected as outside the requested end-of-day documentation scope.
- **Leave unsupported operations inherited.** `TiingoFeed` does not override option-chain methods, so `supports()` and calls behave consistently with the base `DataFeed` unsupported-capability behavior.

## Risks / Trade-offs

- **Token leakage risk** → Do not log tokens, commit tokens, or include tokens in command-line examples; callers must retrieve tokens before constructing `TiingoFeed`.
- **EOD data is not true intraday real time** → Name script and docs as live/manual smoke checks and describe current bars as latest available EOD data.
- **HTTP status mapping may be provider-specific** → Map 401/403 to authentication or entitlement errors, 404/empty payloads to unavailable data, 429 to rate limit, timeouts to timeout errors, and malformed payloads to normalization errors.
- **Interval terminology differs by provider** → Translate `None` to Tiingo `daily`; pass supported Tiingo resampling values through as `resampleFreq` and reject/normalize unsupported values with existing feed errors.

## Migration Plan

- Add `feed/tiingo.py`, export `TiingoFeed` in `feed/__init__.py`, and add unit tests using fake HTTP responses.
- Add `scripts/test_tiingo_download.py` that accepts a token argument and passes it to `TiingoFeed` while exercising current and historical bar calls against a small ticker such as `SPY`.
- No data migration is required. Rollback is removal of the Tiingo adapter export, tests, and script.

## Open Questions

- Should non-daily resampling values be limited to Tiingo EOD values (`daily`, `weekly`, `monthly`, `annually`) or passed through for future Tiingo compatibility?