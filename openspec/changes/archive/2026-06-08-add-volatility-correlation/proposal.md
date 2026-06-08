## Why

We want to know whether a trading day's range (a simple volatility proxy) carries
information about the next day's range. Today there is no tool in the repository
that quantifies this volatility autocorrelation, so the relationship between the
range of day `t` and day `t+1` cannot be measured from our own data feeds.

## What Changes

- Add an analysis script under `scripts/` that measures the correlation between the
  daily range of day `t` and the daily range of day `t+1` for a given ticker.
- Fetch historical daily OHLC bars through the existing provider-independent `feed`
  package (Yahoo by default, no credentials required) over a configurable date range.
- Compute a per-day range series from each `Bar` and pair `range[t]` with
  `range[t+1]` to compute a Pearson correlation coefficient.
- Support a configurable lag (default `1`) and a configurable range definition
  (absolute `high - low` by default, with a normalized `(high - low) / close` option).
- Print a concise, human-readable result (ticker, sample size, lag, correlation)
  using only the Python standard library so no new dependency is introduced.

## Capabilities

### New Capabilities

- `volatility-correlation`: A repository analysis script that measures the
  correlation between a ticker's daily range on consecutive days using historical
  bars from the `feed` package.

### Modified Capabilities

- None.

## Impact

- Affected code: `scripts/` (new analysis script).
- Public API: No changes to the `feed` package public API; the script only consumes
  existing `DataFeed.get_historical_bars` and the `Bar` model.
- Dependencies: None added; correlation is computed with `statistics.correlation`
  from the standard library (available on the project's `>=3.10` Python).
- External systems: Uses the existing Yahoo-backed feed for daily bars by default.
