## Context

The repository already exposes a provider-independent `feed` package whose
`DataFeed.get_historical_bars` returns a list of `Bar` models (ticker, timestamp,
`open`/`high`/`low`/`close` as `Decimal`, volume, optional interval). `YahooFeed`
implements historical daily bars without credentials, while `TiingoFeed` requires a
token. The existing `scripts/` files (`test_yahoo_download.py`,
`test_tiingo_download.py`) are small async entry points that import from `feed`,
adjust `sys.path` to the repo root, and run under `asyncio.run`.

We need a small standalone analysis script that quantifies whether a day's range
predicts the next day's range. The project targets Python `>=3.10`, so
`statistics.correlation` is available and lets us avoid pulling in numpy/scipy.

## Goals / Non-Goals

**Goals:**
- Provide a runnable `scripts/` script that measures the correlation between the
  daily range of day `t` and day `t+lag` for one ticker.
- Reuse the existing `feed` package and `Bar` model for data access.
- Default to the credential-free Yahoo feed and the standard library for stats.
- Keep the script small, readable, and consistent with the existing scripts.

**Non-Goals:**
- No new package dependency (numpy, pandas, scipy) is introduced.
- No persistence of results, plotting, or multi-ticker batch analysis.
- No changes to the `feed` package public API or models.
- No statistical significance testing beyond the correlation coefficient itself.

## Decisions

- **Data source via `feed`.** The script calls `YahooFeed().get_historical_bars`
  with `interval="1d"` over a date range. Rationale: reuses normalized `Bar` data
  and avoids a second data-access path. Alternative considered: reading provider APIs
  directly — rejected because it duplicates feed logic and normalization.

- **Default feed is Yahoo (credential-free).** Rationale: lets a developer run the
  analysis with zero setup. Tiingo would force a token argument for an exploratory
  script. Keeping the feed choice internal (Yahoo) keeps the CLI minimal; switching
  providers later is a small follow-up if needed.

- **Range definition.** Default range is `high - low`; a normalized option computes
  `(high - low) / close`. Rationale: absolute range is the simplest volatility proxy
  the user asked for, while normalized range makes ranges comparable across price
  levels. Both are computed from existing `Bar` fields.

- **Lag pairing.** Build an ordered range series (sorted by `Bar.timestamp`) and pair
  `range[i]` with `range[i + lag]`, default `lag = 1`. Rationale: directly answers
  "is today's range correlated to tomorrow's range" and generalizes to longer lags.

- **Correlation via `statistics.correlation`.** Use the standard library Pearson
  correlation on the two paired lists. Rationale: no new dependency, available on
  Python 3.10+. `Decimal` values are converted to `float` before correlation since
  `statistics.correlation` operates on real numbers. Alternative considered: manual
  Pearson formula — rejected as redundant given the stdlib function.

- **CLI shape.** A small `argparse` (or simple `sys.argv`) interface accepts ticker,
  date range / lookback, lag, and a normalized-range flag, mirroring the lightweight
  style of the existing scripts. The script runs under `asyncio.run` because the feed
  methods are async, and adjusts `sys.path` to the repo root like the sibling scripts.

## Risks / Trade-offs

- [Pearson only captures linear association] → Document this in the output/header;
  a normalized-range option reduces price-level distortion. Rank correlation can be a
  later addition if needed.
- [Yahoo data gaps or holidays create uneven spacing] → Pairing is done on the
  ordered returned bars, so each pair is consecutive trading days as delivered by the
  feed; this is an accepted simplification noted in the script.
- [Small samples give unstable correlations] → The script requires at least two
  paired observations and prints the sample size so the developer can judge reliability.
- [`Decimal`→`float` conversion loses minor precision] → Acceptable for a volatility
  correlation estimate; magnitudes involved are well within float precision.
