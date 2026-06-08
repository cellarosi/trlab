"""Quick live smoke checks for TiingoFeed.

Requires a Tiingo token passed as a command-line argument.

Run with:
    poetry run python -m scripts.test_tiingo_download <token>
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feed import Bar, TiingoFeed


async def test_current_bar(feed: TiingoFeed) -> None:
    """Download the latest available EOD bar for a provider-ready ticker."""

    bar = await feed.get_current_bar("SPY", interval="daily")
    assert isinstance(bar, Bar)
    print("current bar:", bar.ticker, bar.timestamp.date(), bar.close, bar.volume)


async def test_historical_bars(feed: TiingoFeed) -> None:
    """Download a short historical EOD bar range for a provider-ready ticker."""

    end = date.today()
    start = end - timedelta(days=10)
    bars = await feed.get_historical_bars("SPY", start=start, end=end, interval="daily")
    assert bars and all(isinstance(bar, Bar) for bar in bars)
    print("historical bars:", len(bars), bars[0].ticker, bars[-1].timestamp.date(), bars[-1].close)


async def main() -> None:
    """Run one live smoke check per implemented TiingoFeed method."""

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.test_tiingo_download <token>")
    feed = TiingoFeed(api_token=sys.argv[1])
    await test_current_bar(feed)
    await test_historical_bars(feed)


if __name__ == "__main__":
    asyncio.run(main())
