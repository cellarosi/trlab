# ---- GEX Sync Daemon ----
# Minimal image: Python 3.13 Alpine + script only (~50 MB compressed)
# No pip packages needed — the daemon uses only stdlib.
#
# Build:
#   docker build -t gex-sync .
#
# Run (defaults to today's expiration):
#   docker run --rm -v $(pwd)/db:/app/db gex-sync
#
# Run with a specific future expiration (recommended):
#   docker run --rm -v $(pwd)/db:/app/db gex-sync 2026-08-15
#
# Plot collected data:
#   docker run --rm -v $(pwd)/db:/app/db gex-sync --plot

FROM python:3.13-alpine

# tzdata provides the IANA timezone database needed by ZoneInfo("Europe/Rome")
RUN apk add --no-cache tzdata

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY scripts/gex_sync.py .

RUN mkdir -p db

ENTRYPOINT ["python", "gex_sync.py"]
