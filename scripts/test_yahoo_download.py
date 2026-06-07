"""Quick live smoke checks for YahooFeed.

Run with:
    poetry run python scripts/test_yahoo_download.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feed import Bar, OptionChain, YahooFeed


async def test_current_bar(feed: YahooFeed) -> None:
    """Download one current/delayed bar for a provider-ready ticker."""

    bar = await feed.get_current_bar("SPY", interval="1d")
    assert isinstance(bar, Bar)
    print("current bar:", bar.ticker, bar.close, bar.volume)


async def test_historical_bars(feed: YahooFeed) -> None:
    """Download a short historical bar range for a provider-ready ticker."""

    end = date.today()
    start = end - timedelta(days=10)
    bars = await feed.get_historical_bars("SPY", start=start, end=end, interval="1d")
    assert bars and all(isinstance(bar, Bar) for bar in bars)
    print("historical bars:", len(bars), bars[0].ticker, bars[-1].close)


async def test_current_option_chain(feed: YahooFeed) -> None:
    """Download the current/default option chain for an underlying ticker."""

    chain = await feed.get_current_option_chain("SPY")
    assert isinstance(chain, OptionChain)
    print("option chain:", chain.underlying_ticker, chain.expiration, len(chain.contracts))


async def main() -> None:
    """Run one live smoke check per implemented YahooFeed method."""

    feed = YahooFeed()
    await test_current_bar(feed)
    await test_historical_bars(feed)
    await test_current_option_chain(feed)


if __name__ == "__main__":
    asyncio.run(main())