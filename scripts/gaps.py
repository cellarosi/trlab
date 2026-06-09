# Prendi come argomento un ticker, scarica tutti i dati possibili da yahoo formato giornaliero
# e calcola la distribuzione dei gap ovvero lo scarto fra close al tempo T rispetto alla open al tempo T+1
"""Compute the distribution of overnight gaps for a ticker.

A gap is the difference between the open at day t+1 and the close at day t,
expressed both in absolute price terms and as a percentage of the prior close.
All available daily history from Yahoo is downloaded.

Run with:
    poetry run python scripts/gaps.py SPY
    poetry run python scripts/gaps.py SPY --bins 30
    poetry run python scripts/gaps.py SPY --start 2020-01-01 --end 2024-12-31
    poetry run python scripts/gaps.py SPY --vix 20
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feed import Bar, DataFeedError, YahooFeed


WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the gap distribution analysis."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticker", help="Provider-ready ticker symbol, e.g. SPY")
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD); defaults to all available history",
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD); defaults to today",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=20,
        help="Number of histogram bins for the gap distribution (default: 20)",
    )
    parser.add_argument(
        "--vix-ticker",
        default="^VIX",
        help="Ticker used to relate volatility to the gaps (default: ^VIX)",
    )
    parser.add_argument(
        "--vix",
        type=float,
        default=None,
        help="Only keep gaps whose close-day VIX is below this level (default: keep all)",
    )
    return parser.parse_args()


def compute_gaps(
    bars: list[Bar],
) -> tuple[list[float], list[float], list[int], list[date]]:
    """Return absolute and percentage gaps between close[t] and open[t+1].

    The weekday and date returned for each gap are those of the close day t, so
    e.g. Mon means the gap from Monday's close to Tuesday's open.
    """

    absolute: list[float] = []
    percent: list[float] = []
    weekdays: list[int] = []
    dates: list[date] = []
    for prev, current in zip(bars, bars[1:]):
        if prev.close == 0:
            continue
        gap = float(current.open - prev.close)
        absolute.append(gap)
        percent.append(gap / float(prev.close) * 100.0)
        weekdays.append(prev.timestamp.weekday())
        dates.append(prev.timestamp.date())
    return absolute, percent, weekdays, dates


def summarize(label: str, values: list[float], unit: str) -> None:
    """Print summary statistics for a list of gap values."""

    if not values:
        print(f"  {label}: no data.")
        return
    mean = statistics.mean(values)
    median = statistics.median(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    positive = sum(1 for v in values if v > 0)
    negative = sum(1 for v in values if v < 0)
    flat = len(values) - positive - negative
    print(f"  {label}:")
    print(f"    count : {len(values)}")
    print(f"    mean  : {mean:.4f}{unit}")
    print(f"    median: {median:.4f}{unit}")
    print(f"    stdev : {stdev:.4f}{unit}")
    print(f"    min   : {min(values):.4f}{unit}")
    print(f"    max   : {max(values):.4f}{unit}")
    print(f"    up/down/flat: {positive}/{negative}/{flat}")


def summarize_by_weekday(percent: list[float], weekdays: list[int]) -> None:
    """Print mean and count of percentage gaps grouped by close-day weekday."""

    print("  by weekday (close day -> next open):")
    for day in range(5):
        values = [p for p, w in zip(percent, weekdays) if w == day]
        if not values:
            print(f"    {WEEKDAY_NAMES[day]}: no data.")
            continue
        mean = statistics.mean(values)
        median = statistics.median(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        positive = sum(1 for v in values if v > 0)
        negative = sum(1 for v in values if v < 0)
        print(
            f"    {WEEKDAY_NAMES[day]}: mean {mean:+.4f}% median {median:+.4f}% "
            f"stdev {stdev:.4f}% up/down {positive}/{negative} (n={len(values)})"
        )


def _vix_suffix(vix_by_date: dict[date, float] | None, day: date) -> str:
    """Return a formatted VIX close suffix for a tail line, if available."""

    if not vix_by_date:
        return ""
    level = vix_by_date.get(day)
    return f" (VIX {level:.2f})" if level is not None else " (VIX n/a)"


def print_tails(
    percent: list[float],
    dates: list[date],
    num_std: float = 2.0,
    vix_by_date: dict[date, float] | None = None,
) -> None:
    """List the close dates of gaps beyond ``num_std`` std on each side of the mean."""

    if len(percent) < 2:
        return
    mean = statistics.mean(percent)
    stdev = statistics.stdev(percent)
    low = mean - num_std * stdev
    high = mean + num_std * stdev

    negative = sorted(
        ((d, p) for d, p in zip(dates, percent) if p < low),
        key=lambda item: item[0],
    )
    print(
        f"  negative tail (gap < mean - {num_std:g} std = {low:.4f}%, "
        f"{len(negative)} day(s)):"
    )
    for d, p in negative:
        print(f"    {d.isoformat()}: {p:.4f}%{_vix_suffix(vix_by_date, d)}")

    positive = sorted(
        ((d, p) for d, p in zip(dates, percent) if p > high),
        key=lambda item: item[0],
    )
    print(
        f"  positive tail (gap > mean + {num_std:g} std = {high:.4f}%, "
        f"{len(positive)} day(s)):"
    )
    for d, p in positive:
        print(f"    {d.isoformat()}: {p:.4f}%{_vix_suffix(vix_by_date, d)}")


def print_vix_relation(
    percent: list[float], dates: list[date], vix_by_date: dict[date, float]
) -> None:
    """Relate the VIX close on day t to the size and sign of the gap into t+1."""

    vix: list[float] = []
    gap: list[float] = []
    abs_gap: list[float] = []
    for d, p in zip(dates, percent):
        level = vix_by_date.get(d)
        if level is None:
            continue
        vix.append(level)
        gap.append(p)
        abs_gap.append(abs(p))
    print(f"  VIX relation ({len(vix)} matched day(s)):")
    if len(vix) < 2:
        print("    not enough matched data.")
        return
    print(f"    VIX[t] vs |gap%|: corr {statistics.correlation(vix, abs_gap):+.4f}")
    print(f"    VIX[t] vs gap%  : corr {statistics.correlation(vix, gap):+.4f}")


def histogram(values: list[float], bins: int, unit: str) -> None:
    """Print a simple text histogram of the gap distribution."""

    if not values or bins < 1:
        return
    low = min(values)
    high = max(values)
    if low == high:
        print(f"    all values equal to {low:.4f}{unit}")
        return
    width = (high - low) / bins
    counts = [0] * bins
    for value in values:
        index = min(int((value - low) / width), bins - 1)
        counts[index] += 1
    peak = max(counts)
    print(f"  histogram ({bins} bins):")
    for i, count in enumerate(counts):
        edge_low = low + i * width
        edge_high = edge_low + width
        bar = "#" * round(count / peak * 40) if peak else ""
        print(f"    [{edge_low:8.3f}, {edge_high:8.3f}{unit}) {count:5d} {bar}")


async def fetch_vix_closes(
    feed: YahooFeed, ticker: str, start: date, end: date
) -> dict[date, float]:
    """Download VIX daily closes keyed by date, or empty on failure."""

    try:
        bars = await feed.get_historical_bars(ticker, start=start, end=end, interval="1d")
    except DataFeedError as exc:
        print(f"Warning: could not retrieve VIX ({ticker}): {exc}")
        return {}
    return {bar.timestamp.date(): float(bar.close) for bar in bars}


async def run(args: argparse.Namespace) -> int:
    """Fetch all daily bars, compute gaps, and print the distribution."""

    if args.bins < 1:
        print("Error: --bins must be a positive integer.")
        return 2

    try:
        start = date.fromisoformat(args.start) if args.start else date(1900, 1, 1)
        end = date.fromisoformat(args.end) if args.end else date.today()
    except ValueError as exc:
        print(f"Error: invalid date: {exc}.")
        return 2
    if start >= end:
        print("Error: start date must be before end date.")
        return 2

    feed = YahooFeed()
    try:
        bars = await feed.get_historical_bars(
            args.ticker, start=start, end=end, interval="1d"
        )
    except DataFeedError as exc:
        print(f"Error: could not retrieve bars for {args.ticker}: {exc}")
        return 1

    bars = sorted(bars, key=lambda bar: bar.timestamp)
    if len(bars) < 2:
        print(f"Error: not enough bars for {args.ticker} ({len(bars)}).")
        return 1

    vix_by_date = await fetch_vix_closes(feed, args.vix_ticker, start, end)

    absolute, percent, weekdays, dates = compute_gaps(bars)
    print(
        f"{args.ticker}: overnight gap distribution "
        f"({bars[0].timestamp.date().isoformat()} to "
        f"{bars[-1].timestamp.date().isoformat()}, {len(bars)} bars):"
    )

    if args.vix is not None:
        if not vix_by_date:
            print(f"Error: no VIX data to filter on (--vix {args.vix:g}).")
            return 1
        kept = [
            i
            for i, d in enumerate(dates)
            if vix_by_date.get(d) is not None and vix_by_date[d] < args.vix
        ]
        absolute = [absolute[i] for i in kept]
        percent = [percent[i] for i in kept]
        weekdays = [weekdays[i] for i in kept]
        dates = [dates[i] for i in kept]
        print(f"  filter: close-day VIX < {args.vix:g} ({len(percent)} gap(s) kept).")
        if len(percent) < 2:
            print("  not enough gaps after VIX filter.")
            return 0

    summarize("absolute (open[t+1] - close[t])", absolute, "")
    summarize("percent (relative to close[t])", percent, "%")
    summarize_by_weekday(percent, weekdays)
    histogram(percent, args.bins, "%")
    if vix_by_date:
        print_vix_relation(percent, dates, vix_by_date)
    print_tails(percent, dates, vix_by_date=vix_by_date)
    return 0


def main() -> None:
    """Entry point for the gap distribution analysis script."""

    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()