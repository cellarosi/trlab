"""Tests for market data feed interfaces."""

from __future__ import annotations

from datetime import date
import inspect
import sys
import unittest
from typing import Any

import feed
from feed import DataFeed, UnsupportedCapabilityError, YahooFeed
from symbols.models import Symbol


class FeedImportTests(unittest.TestCase):
    def test_feed_imports_without_yahoo_specific_dependency(self) -> None:
        """Verify the public feed API imports without loading Yahoo libraries."""

        self.assertIs(feed.DataFeed, DataFeed)
        self.assertIs(feed.YahooFeed, YahooFeed)
        self.assertNotIn("yfinance", sys.modules)


class DataFeedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.symbol = Symbol(ticker="SPY", type="ETF", contracts=["SPY"])

    def test_operation_methods_are_present_and_async(self) -> None:
        """Verify every declared DataFeed operation exists and is async."""

        data_feed = DataFeed()
        for operation in DataFeed._operations:
            with self.subTest(operation=operation):
                method = getattr(data_feed, operation)
                self.assertTrue(inspect.iscoroutinefunction(method))

    async def test_base_operations_raise_unsupported_capability_error(self) -> None:
        """Verify base DataFeed methods fail with the normalized unsupported error."""

        data_feed = DataFeed()
        calls = [
            data_feed.get_current_bar(self.symbol),
            data_feed.get_current_option_chain(self.symbol),
            data_feed.get_historical_bars(self.symbol, date(2024, 1, 1), date(2024, 1, 2)),
            data_feed.get_historical_option_chain(self.symbol, date(2024, 1, 1)),
        ]

        for call in calls:
            with self.subTest(call=call):
                # Base-class operations are intentionally unsupported until a
                # concrete provider overrides the specific operation.
                with self.assertRaises(UnsupportedCapabilityError):
                    await call

    def test_supports_reports_inherited_overridden_and_unknown_operations(self) -> None:
        """Verify supports() distinguishes overrides from inherited defaults."""

        class CurrentBarFeed(DataFeed):
            """Minimal feed used to prove overridden operations are supported."""

            async def get_current_bar(
                self, symbol: Symbol, interval: str | None = None
            ) -> Any:
                return {"symbol": symbol.ticker, "interval": interval}

        base_feed = DataFeed()
        current_bar_feed = CurrentBarFeed()

        self.assertFalse(base_feed.supports("get_current_bar"))
        self.assertTrue(current_bar_feed.supports("get_current_bar"))
        self.assertFalse(current_bar_feed.supports("get_historical_bars"))
        self.assertFalse(current_bar_feed.supports("unknown_operation"))

    async def test_yahoo_feed_is_data_feed_and_inherits_unsupported_behavior(self) -> None:
        """Verify YahooFeed is only a skeleton and inherits unsupported methods."""

        yahoo_feed = YahooFeed()

        self.assertIsInstance(yahoo_feed, DataFeed)
        self.assertFalse(yahoo_feed.supports("get_current_bar"))
        with self.assertRaises(UnsupportedCapabilityError):
            await yahoo_feed.get_current_bar(self.symbol)


if __name__ == "__main__":
    unittest.main()