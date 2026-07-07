# trlab — GEX Sync

A polling daemon that fetches SPX Gamma Exposure (GEX) data from [quantwheel.com](https://quantwheel.com) every minute and appends it to a local CSV. Includes a plotting utility for visualizing Call Wall, Put Wall, and underlying price over time, with gamma-zone background shading.

Full architecture, design rationale, API details, and test coverage are documented in **[misc/GEX.md](misc/GEX.md)**.

## Quickstart

```bash
# Install deps (plotting only — daemon is stdlib-only)
poetry install

# Run the sync daemon for a specific expiration
poetry run python scripts/gex_sync.py 2026-08-15

# Plot collected data
poetry run python scripts/gex_sync.py --plot

# Run tests (48 tests, all passing)
cd tests && python3 -m unittest test_gex_sync -v
```

## Docker

```bash
# Build (~74 MB uncompressed, ~30 MB on registry)
docker build -t gex-sync .

# Run the daemon (mount db/ to persist CSV)
docker run --rm -v $(pwd)/db:/app/db gex-sync 2026-08-15

# Plot existing data
docker run --rm -v $(pwd)/db:/app/db gex-sync --plot
```

### docker-compose

Auto-restart on crash. Runs indefinitely, mounting `./db` for persistence:

```bash
docker compose up -d        # start in background
docker compose logs -f      # tail logs
docker compose down         # stop
```

The `restart: always` policy ensures the container comes back after a crash or Docker daemon restart.

The image uses `python:3.13-alpine` with only `tzdata` added — the daemon uses zero pip packages (stdlib only: `urllib`, `json`, `os`, `time`, `datetime`).

## How it works

- **Polling loop**: every 5 seconds during the GEX window (15:30–21:59 Europe/Rome)
- **Time bucketing**: rows are written once per minute bucket (configurable via `BUCKET_MINUTES`)
- **Duplicate guard**: in-memory + on-disk deduplication (survives restarts)
- **CSV output**: `datetime,expiration,callWall_strike,putWall_strike,gammaInflection,gammaZone,underlyingPrice`
- **Plotting**: matplotlib chart with Call Wall / Put Wall lines and gamma-zone background shading (`--plot`)

## Project structure

```
trlab/
├── scripts/gex_sync.py      # Production code — daemon + plotting
├── tests/test_gex_sync.py   # 48 unit tests
├── db/
│   ├── gex.csv              # Live CSV (appended in production)
│   └── old/                 # Historical .parquet snapshots
├── Dockerfile               # python:3.13-alpine, stdlib-only
├── docker-compose.yml       # auto-restart orchestration
├── pyproject.toml           # Poetry config (matplotlib/pandas for plotting)
└── misc/GEX.md              # Full architecture & design doc
```
