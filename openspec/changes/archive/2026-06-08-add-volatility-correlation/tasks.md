## 1. Script Skeleton and CLI

- [x] 1.1 Add `scripts/range_correlation.py` with a module docstring and the `poetry run` usage example, mirroring the existing scripts.
- [x] 1.2 Insert the repo root on `sys.path` and import `Bar` and `YahooFeed` from `feed`.
- [x] 1.3 Parse CLI arguments for ticker, date range (or lookback days), lag (default `1`), a normalized-range flag, and an optional `--weekday` filter.
- [x] 1.4 Validate that lag is a positive integer and report a clear error otherwise.

## 2. Data Retrieval

- [x] 2.1 Construct `YahooFeed` and call `get_historical_bars` with `interval="1d"` for the requested ticker and date range.
- [x] 2.2 Sort the returned bars by `Bar.timestamp` to ensure chronological order.

## 3. Range and Correlation Computation

- [x] 3.1 For each run, compute three range types (cumulative `high - low`, positive, negative): predictor day `t` measured from `open`, target day `t+lag` measured from the prior day's `close` to include the overnight gap, each optionally divided by its own entry price (predictor `open`, target prior `close`) when the normalized flag is set.
- [x] 3.2 Convert range values to `float` for use with the standard library statistics.
- [x] 3.3 Build paired series by aligning the day-`t` predictor range with the day-`t+lag` gap-inclusive target range, keeping only pairs whose predictor day matches `--weekday` when given.
- [x] 3.4 Compute the Pearson correlation using `statistics.correlation` on the paired series.
- [x] 3.5 Handle the insufficient-data case (fewer than two pairs) with a clear message instead of an unhandled error.

## 4. Output

- [x] 4.1 Print a concise summary including ticker, lag, date range, and the cumulative, positive, and negative range correlation coefficients with their paired observation counts.
- [x] 4.2 Note in the script header that the result is a Pearson (linear) correlation over consecutive returned trading days.

## 5. Verification

- [x] 5.1 Run the script for a liquid ticker (e.g. `SPY`) over a multi-month range and confirm it prints a correlation result.
- [x] 5.2 Confirm a non-positive lag and an empty date range each produce clear, handled error messages.
- [x] 5.3 Confirm no new dependency was added to `pyproject.toml`.
- [x] 5.4 Confirm `--weekday` restricts the paired observations and that an invalid weekday is rejected.
