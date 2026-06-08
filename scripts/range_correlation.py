"""Measure correlation between a ticker's daily range on consecutive days.

This computes the Pearson (linear) correlation between the range of day t and the
range of day t+lag over the consecutive trading days returned by the feed, to gauge
whether today's range (a volatility proxy) is correlated with a later day's range.

The day-t (predictor) range is measured from that day's open: positive is
high - open, negative is open - low, cumulative is high - low. The day-t+lag (target)
range is measured from the prior day's close instead of its own open, as if entering
at the previous close, so the overnight gap is incorporated: positive is
high - prev_close, negative is prev_close - low, cumulative is high - low. All three
ranges are always reported. When normalized, each range is divided by its own entry
price (open for the predictor, prior close for the target) to keep the two uniform.

Run with:
    poetry run python scripts/range_correlation.py SPY
    poetry run python scripts/range_correlation.py SPY --lookback 252 --lag 1
    poetry run python scripts/range_correlation.py SPY --normalized --weekday mon
    poetry run python scripts/range_correlation.py SPY --start 2024-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feed import Bar, DataFeedError, YahooFeed


WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the range correlation analysis."""

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticker", help="Provider-ready ticker symbol, e.g. SPY")
    parser.add_argument(
        "--lookback",
        type=int,
        default=252,
        help="Number of calendar days back from today when --start is not given (default: 252)",
    )
    parser.add_argument("--start", help="Start date (YYYY-MM-DD); overrides --lookback")
    parser.add_argument("--end", help="End date (YYYY-MM-DD); defaults to today")
    parser.add_argument(
        "--lag",
        type=int,
        default=1,
        help="Positive day offset to pair range[t] with range[t+lag] (default: 1)",
    )
    parser.add_argument(
        "--normalized",
        action="store_true",
        help="Normalize each range by dividing by its entry price (open for the predictor, prior close for the target)",
    )
    parser.add_argument(
        "--weekday",
        choices=tuple(WEEKDAYS),
        help="Only keep pairs whose predictor day t falls on this weekday (default: all days)",
    )
    return parser.parse_args()


def resolve_range(args: argparse.Namespace) -> tuple[date, date]:
    """Resolve the start and end dates from CLI arguments."""

    end = date.fromisoformat(args.end) if args.end else date.today()
    if args.start:
        start = date.fromisoformat(args.start)
    else:
        start = end - timedelta(days=args.lookback)
    if start >= end:
        raise ValueError("start date must be before end date")
    return start, end


def range_value(bar: Bar, entry: Decimal, range_type: str, normalized: bool) -> float:
    """Return one day's range as a float measured from the given entry price.

    positive: high - entry, negative: entry - low, cumulative: high - low. When
    normalized, the range is divided by the entry price.
    """

    if range_type == "positive":
        value = bar.high - entry
    elif range_type == "negative":
        value = entry - bar.low
    else:
        value = bar.high - bar.low
    if normalized:
        if entry == 0:
            raise ValueError("cannot compute normalized range with a zero entry price")
        value = value / entry
    return float(value)


def range_pairs(
    bars: list[Bar],
    lag: int,
    range_type: str,
    normalized: bool,
    weekday: int | None = None,
) -> tuple[list[float], list[float]]:
    """Pair the day-t predictor range with the day-t+lag target range.

    The predictor range is measured from the predictor day's open. The target range
    is measured from the close of the day immediately before the target day, so the
    overnight gap into the target day is incorporated. When weekday is given, only
    pairs whose predictor day falls on that weekday are kept.
    """

    base: list[float] = []
    target: list[float] = []
    for i in range(len(bars) - lag):
        predictor = bars[i]
        if weekday is not None and predictor.timestamp.weekday() != weekday:
            continue
        target_bar = bars[i + lag]
        prev_close = bars[i + lag - 1].close
        base.append(range_value(predictor, predictor.open, range_type, normalized))
        target.append(range_value(target_bar, prev_close, range_type, normalized))
    return base, target


async def run(args: argparse.Namespace) -> int:
    """Fetch bars, compute the lagged range correlation, and print a summary."""

    if args.lag < 1:
        print("Error: --lag must be a positive integer.")
        return 2

    try:
        start, end = resolve_range(args)
    except ValueError as exc:
        print(f"Error: {exc}.")
        return 2

    feed = YahooFeed()
    try:
        bars = await feed.get_historical_bars(args.ticker, start=start, end=end, interval="1d")
    except DataFeedError as exc:
        print(f"Error: could not retrieve bars for {args.ticker}: {exc}")
        return 1

    bars = sorted(bars, key=lambda bar: bar.timestamp)

    weekday = WEEKDAYS[args.weekday] if args.weekday else None
    prefix = "normalized " if args.normalized else ""
    weekday_note = f", weekday t={args.weekday}" if args.weekday else ""
    print(
        f"{args.ticker}: {prefix}range correlation between day t and day t+{args.lag} "
        f"({start.isoformat()} to {end.isoformat()}{weekday_note}):"
    )
    for range_type in ("cumulative", "positive", "negative"):
        try:
            base, target = range_pairs(bars, args.lag, range_type, args.normalized, weekday)
        except ValueError as exc:
            print(f"  {range_type}: error: {exc}.")
            continue

        if len(base) < 2:
            print(
                f"  {range_type}: not enough data "
                f"({len(base)} paired observation(s), need at least 2)."
            )
            continue

        correlation = statistics.correlation(base, target)
        print(f"  {range_type}: {correlation:.4f} over {len(base)} paired observations.")
    return 0


def main() -> None:
    """Entry point for the range correlation analysis script."""

    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
