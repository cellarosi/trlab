"""Tests for market data feed interfaces."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import inspect
import sys
import unittest
from typing import Any, get_type_hints

from pydantic import ValidationError

import feed
from feed import Bar, DataFeed, OptionChain, OptionContract, OptionRight, UnsupportedCapabilityError, YahooFeed
from symbols.models import Symbol


class FeedImportTests(unittest.TestCase):
    def test_feed_imports_without_yahoo_specific_dependency(self) -> None:
        """Verify the public feed API imports without loading Yahoo libraries."""

        self.assertIs(feed.DataFeed, DataFeed)
        self.assertIs(feed.YahooFeed, YahooFeed)
        self.assertIs(feed.Bar, Bar)
        self.assertIs(feed.OptionContract, OptionContract)
        self.assertIs(feed.OptionChain, OptionChain)
        self.assertIs(feed.OptionRight, OptionRight)
        self.assertNotIn("yfinance", sys.modules)


class FeedModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.symbol = Symbol(ticker="SPY", type="ETF", contracts=["SPY"])

    def test_valid_bar_accepts_normalized_ohlcv_fields(self) -> None:
        """Verify a standard Bar can represent one provider-neutral OHLCV row."""

        bar = Bar(
            symbol=self.symbol,
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
            open="470.10",
            high="472.00",
            low="469.50",
            close="471.25",
            volume=1_000,
            interval="1m",
        )

        self.assertEqual(bar.symbol, self.symbol)
        self.assertEqual(bar.close, Decimal("471.25"))
        self.assertEqual(bar.volume, Decimal("1000"))

    def test_bar_rejects_negative_volume_and_unknown_fields(self) -> None:
        """Verify Bar validation rejects invalid provider data before return."""

        valid_bar = {
            "symbol": self.symbol,
            "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "open": "1",
            "high": "2",
            "low": "1",
            "close": "2",
        }

        with self.assertRaises(ValidationError):
            Bar(**valid_bar, volume=-1)
        with self.assertRaises(ValidationError):
            Bar(**valid_bar, volume=1, provider_payload={"source": "test"})

    def test_valid_option_contract_accepts_normalized_fields(self) -> None:
        """Verify one normalized option row supports quotes, Greeks, and interest."""

        contract = OptionContract(
            underlying_symbol=self.symbol,
            option_symbol="SPY240119C00470000",
            expiration=date(2024, 1, 19),
            strike="470",
            right=OptionRight.CALL,
            bid="1.20",
            ask="1.25",
            delta="0.55",
            volume=10,
            open_interest=250,
        )

        self.assertEqual(contract.right, OptionRight.CALL)
        self.assertEqual(contract.strike, Decimal("470"))
        self.assertEqual(contract.open_interest, 250)

    def test_option_contract_rejects_invalid_right_and_unknown_fields(self) -> None:
        """Verify option contracts only accept call/put rights and known fields."""

        valid_contract = {
            "underlying_symbol": self.symbol,
            "option_symbol": "SPY240119P00470000",
            "expiration": date(2024, 1, 19),
            "strike": "470",
        }

        with self.assertRaises(ValidationError):
            OptionContract(**valid_contract, right="straddle")
        with self.assertRaises(ValidationError):
            OptionContract(**valid_contract, right="put", provider_side="native")

    def test_option_chain_preserves_call_and_put_contract_rows(self) -> None:
        """Verify OptionChain keeps normalized call and put rows in order."""

        call_contract = OptionContract(
            underlying_symbol=self.symbol,
            option_symbol="SPY240119C00470000",
            expiration=date(2024, 1, 19),
            strike="470",
            right="call",
        )
        put_contract = OptionContract(
            underlying_symbol=self.symbol,
            option_symbol="SPY240119P00470000",
            expiration=date(2024, 1, 19),
            strike="470",
            right="put",
        )

        chain = OptionChain(
            underlying_symbol=self.symbol,
            as_of=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
            expiration=date(2024, 1, 19),
            contracts=[call_contract, put_contract],
        )

        self.assertEqual(chain.contracts, [call_contract, put_contract])
        self.assertEqual([contract.right for contract in chain.contracts], [OptionRight.CALL, OptionRight.PUT])


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

    def test_operation_return_annotations_use_standard_models(self) -> None:
        """Verify DataFeed advertises standard provider-independent return types."""

        current_bar_hints = get_type_hints(DataFeed.get_current_bar)
        current_chain_hints = get_type_hints(DataFeed.get_current_option_chain)
        historical_bars_hints = get_type_hints(DataFeed.get_historical_bars)
        historical_chain_hints = get_type_hints(DataFeed.get_historical_option_chain)

        self.assertEqual(current_bar_hints["return"], Bar)
        self.assertEqual(current_chain_hints["return"], OptionChain)
        self.assertEqual(historical_bars_hints["return"], list[Bar])
        self.assertEqual(historical_chain_hints["return"], OptionChain)

    async def test_yahoo_feed_is_data_feed_and_inherits_unsupported_behavior(self) -> None:
        """Verify YahooFeed is only a skeleton and inherits unsupported methods."""

        yahoo_feed = YahooFeed()

        self.assertIsInstance(yahoo_feed, DataFeed)
        self.assertFalse(yahoo_feed.supports("get_current_bar"))
        with self.assertRaises(UnsupportedCapabilityError):
            await yahoo_feed.get_current_bar(self.symbol)


if __name__ == "__main__":
    unittest.main()