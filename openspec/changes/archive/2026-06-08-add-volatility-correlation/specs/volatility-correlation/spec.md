## ADDED Requirements

### Requirement: Volatility correlation analysis script
The system SHALL provide a repository script under `scripts/` that measures the
correlation between a ticker's daily range on day `t` and its daily range on a later
day `t+lag`, using historical daily bars obtained from the `feed` package.

#### Scenario: Script reports next-day range correlation
- **WHEN** a developer runs the script for a provider-ready ticker over a date range with daily bars available
- **THEN** the script pairs each day's range with the range `lag` days later and prints the cumulative, positive, and negative range correlation coefficients

#### Scenario: Script uses a credential-free feed by default
- **WHEN** a developer runs the script without supplying provider credentials
- **THEN** the script retrieves daily bars through the Yahoo-backed feed without requiring a token

### Requirement: Predictor range computation
The system SHALL compute the day `t` predictor range from that day's `open`: the
cumulative range `high - low`, the positive range `high - open`, and the negative range
`open - low`.

#### Scenario: Predictor ranges are measured from the open
- **WHEN** the script computes the day `t` predictor ranges for a day's `Bar`
- **THEN** it computes the cumulative range `high - low`, the positive range `high - open`, and the negative range `open - low`

### Requirement: Gap-inclusive target range computation
The system SHALL compute the day `t+lag` target range from the close of the day
immediately before the target day instead of the target day's own open, so the
overnight gap is incorporated: the positive range is `high - prev_close`, the negative
range is `prev_close - low`, and the cumulative range remains `high - low`.

#### Scenario: Target ranges are measured from the prior day's close
- **WHEN** the script computes the day `t+lag` target ranges
- **THEN** the positive range is `high - prev_close`, the negative range is `prev_close - low`, and the cumulative range is `high - low`, where `prev_close` is the close of the day before the target day

#### Scenario: Overnight gap is incorporated into the target range
- **WHEN** the target day opens away from the prior day's close
- **THEN** the target positive and negative ranges reflect the move relative to the prior day's close rather than the target day's open

### Requirement: Uniform normalization by entry price
The system SHALL support a normalized variant that divides each range by its own entry
price uniformly across the predictor and target: the predictor ranges by the day `t`
`open` and the target ranges by the prior day's close used as the entry price.

#### Scenario: Predictor ranges normalize by the open
- **WHEN** the script is run with the normalized option
- **THEN** each day `t` predictor range is divided by that day's `open`

#### Scenario: Target ranges normalize by the prior day's close
- **WHEN** the script is run with the normalized option
- **THEN** each day `t+lag` target range is divided by the prior day's close used as its entry price

### Requirement: Weekday filter
The system SHALL accept an optional weekday parameter and, when given, SHALL keep only
the pairs whose predictor day `t` falls on that weekday, defaulting to all days.

#### Scenario: Weekday filter restricts predictor days
- **WHEN** the script is run with a weekday value
- **THEN** it only includes pairs whose predictor day `t` falls on that weekday

#### Scenario: No weekday filter keeps all days
- **WHEN** the script is run without a weekday value
- **THEN** it includes pairs for every predictor day in the range

#### Scenario: Invalid weekday is rejected
- **WHEN** the script is run with an unrecognized weekday value
- **THEN** the script reports an error and does not compute a correlation

### Requirement: Configurable lag
The system SHALL pair each day's range with the range `lag` days later, defaulting to
a lag of `1` (day `t` paired with day `t+1`), and SHALL accept a positive integer lag.

#### Scenario: Default lag pairs consecutive days
- **WHEN** the script is run without a lag option
- **THEN** it pairs the range of day `t` with the range of day `t+1`

#### Scenario: Custom lag is honored
- **WHEN** the script is run with a positive integer lag value
- **THEN** it pairs the range of day `t` with the range of day `t+lag`

#### Scenario: Invalid lag is rejected
- **WHEN** the script is run with a non-positive lag value
- **THEN** the script reports an error and does not compute a correlation

### Requirement: Correlation computation without new dependencies
The system SHALL compute the Pearson correlation coefficient between the paired range
series using only the Python standard library and SHALL NOT introduce a new package
dependency.

#### Scenario: Correlation uses the standard library
- **WHEN** the script computes the correlation between the paired range series
- **THEN** it relies on the standard library and adds no new third-party dependency

#### Scenario: Insufficient data is handled
- **WHEN** the requested ticker and date range yield fewer than two paired observations
- **THEN** the script reports that there is not enough data instead of raising an unhandled error

### Requirement: Concise analysis output
The system SHALL print a concise, human-readable summary of the analysis result.

#### Scenario: Summary reports the analysis inputs and result
- **WHEN** the script finishes a successful run
- **THEN** it prints the ticker, the number of paired observations, the lag used, and the correlation coefficient
