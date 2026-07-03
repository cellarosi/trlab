# GEX Sync — Agent Session Handoff

## What this is

A polling daemon that fetches SPX Gamma Exposure (GEX) data from [quantwheel.com](https://quantwheel.com) every 15 minutes and appends it to a local CSV (`gex.csv`). The script runs indefinitely, writing a new row only when a new 15-minute bucket is entered.

## Files

| File | Role |
|---|---|
| `scripts/gex_sync.py` | Production code — the polling daemon |
| `scripts/test_gex_sync.py` | Unit tests — 41 tests, all passing |
| `scripts/GEX.md` | This document |

## How to run

```bash
# With a specific expiration date
poetry run python scripts/gex_sync.py 2026-07-06

# Defaults to today's date (usually a 404 — see "Known issues")
poetry run python scripts/gex_sync.py
```

Tests:
```bash
cd scripts && python3 -m unittest test_gex_sync -v
```

## CSV output format

```
datetime,expiration,callWall_strike,putWall_strike,gammaInflection,gammaZone,stockPrice
2026-07-03 20:00:00,2026-07-06 00:00:00,7500,7450,7473.63,positive,7483.24
2026-07-03 20:15:00,2026-07-06 00:00:00,7500,7450,7473.63,positive,7483.24
```

- `datetime` — floored to the nearest 15-minute mark (always `:00`, `:15`, `:30`, or `:45`)
- `expiration` — the option expiration date, padded with ` 00:00:00` to match the datetime format
- All other fields come directly from the API response

## Architecture & design decisions

### Time bucketing

The 15-minute bucket is computed with integer division:

```python
(dt.minute // 15) * 15   # → 0, 15, 30, or 45
```

This replaces an earlier 4-branch `if/elif` chain. Minute 59 correctly floors to 45 (not 60).

### Dual duplicate guard

Two layers prevent duplicate rows:

1. **In-memory** (`floored == last`): skips the fetch + disk check entirely once we've already seen this interval in the current process. Cheap, no I/O.
2. **On-disk** (`_already_in_csv`): catches restarts. If the script is killed and relaunched within the same 15-min window, it reads `gex.csv` and skips rows that already exist. More expensive (file read) but only runs once per interval.

The `_already_in_csv` check uses `line.startswith(ts)` rather than exact match. This is deliberately loose: `"2026-07-03 10:00:00"` would also match `"2026-07-03 10:00:00.123"` if that ever appeared. In practice `ts` is always in `YYYY-MM-DD HH:MM:SS` format so this only affects same-second collisions (which are fine — they're the same interval).

### CSV appending

- `write_gex_csv` returns `bool` — `True` if a row was written, `False` if duplicate-skipped. This is used by the test suite.
- Header `CSV_HEADER` is written only when the file is empty/missing.
- Rows are always appended (`"a"` mode). The file grows monotonically.

### API authentication

The quantwheel.com API has a rate limit: ~2 anonymous requests before returning `{"error": "Daily GEX limit reached. Sign in for more access."}` (HTTP 200 with error payload).

`QUANTWHEEL_COOKIE` contains browser session cookies extracted from DevTools → Application → Cookies → quantwheel.com. Format: `key=value; key=value; ...`. The critical cookie is `__Secure-authjs.session-token` — without it, the API rate-limits immediately.

To refresh: open quantwheel.com in a browser, sign in, copy the cookie string from any authenticated request header, and paste it into `QUANTWHEEL_COOKIE`.

### Why no `requests` library

The script uses only stdlib (`urllib.request`, `json`, `os`, `time`, `datetime`). No external dependencies needed beyond Python 3. This was a deliberate choice to keep the test suite dependency-free and the script runnable in any environment.

### Why `None` is stringified to `"None"` in CSV

When `fetch_gex` returns `None` (failure), the fields default to `""` (empty string). But if a field is genuinely `None` (Python `None`), `_format_csv_row` stringifies it to `"None"`. This is intentional: an empty cell would silently hide missing data, while `"None"` is explicit and greppable.

## API details

**Endpoint:** `GET https://quantwheel.com/api/tools/gex`

**Parameters:**
| Param | Value |
|---|---|
| `ticker` | `SPX` |
| `expirations` | Date like `2026-07-06` |
| `deltaRange` | `all` |
| `formula` | `per_1pct` |

**Response shape (HTTP 200):**
```json
{
  "data": [ ... ],           // 57 strike-level GEX rows
  "totalGEX": -87785861654,
  "callWall": {"strike": 7500, "gex": 68855103974},
  "putWall":  {"strike": 7450, "gex": -86385049649},
  "gammaInflection": 7473.63,
  "gammaZone": "positive",
  "stockPrice": 7483.24,
  "meta": { ... }
}
```

**Error responses:**
- `404` — no data for that expiration (e.g., today's date)
- `429` — rate limit (anonymous requests)
- `200` + `{"error": "..."}` — daily limit reached or other API-level error

## Known issues

1. **Today's date returns 404.** The API serves future expirations only. Pass a future date explicitly.
2. **Session cookie expires.** The `__Secure-authjs.session-token` has an expiration (visible in the cookie table). When requests start failing with 429 again, refresh the cookie from the browser.
3. **No retry on fetch failure.** If `fetch_gex` returns `None`, the row is still written with empty values. A next iteration could add exponential backoff.
4. **Day boundary.** Expiration is passed as a CLI arg and never changes. If the script runs past midnight into a new trading day, the expiration may become stale.

## Test suite

41 tests covering every code path:

| Class | Tests | What it covers |
|---|---|---|
| `TestGet15minInterval` | 12 | All 4 buckets, boundary edges (0, 14, 15, 29, 30, 44, 45, 59) |
| `TestFloorTo15min` | 7 | All buckets, seconds/microseconds zeroed, midnight boundary |
| `TestBuildGexUrl` | 2 | URL formation with different expirations |
| `TestAlreadyInCsv` | 7 | File missing, empty, not-found, found, header collision, prefix matching, multi-row |
| `TestFormatCsvRow` | 5 | Full values, `None`, empty strings, floats, expiration midnight padding |
| `TestWriteGexCsv` | 10 | New file, append, duplicate skip, all 4 buckets, `None`/empty values, 3-4 interval sequences |

Tests use `tempfile.NamedTemporaryFile` with `delete=False` + manual cleanup. This avoids OS locks (some platforms prevent re-opening a `NamedTemporaryFile` while its handle is open).

## Future directions (ideas for next session)

- Add a `--once` flag to run a single fetch and exit (useful for cron)
- Multi-expiration support: poll several expirations and write to separate CSV columns
- Exponential backoff on HTTP errors
- `pd.read_csv` integration: detect and surface the `None` string → actual `None` conversion
- Grafana / dashboard ingestion from the CSV
