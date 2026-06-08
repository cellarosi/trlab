"""Tests for market data feed interfaces."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import inspect
import json
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
from typing import Any, get_type_hints
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pandas as pd
from pydantic import ValidationError

import feed
from feed import (
    Bar,
    DataFeed,
    DataFeedAuthenticationError,
    DataFeedError,
    DataFeedTimeoutError,
    DataUnavailableError,
    EntitlementError,
    MissingProviderMappingError,
    NetworkError,
    NormalizationError,
    OptionChain,
    OptionContract,
    OptionRight,
    RateLimitError,
    TiingoFeed,
    UnsupportedCapabilityError,
    YahooFeed,
)


class FeedImportTests(unittest.TestCase):
    def test_feed_imports_without_yahoo_specific_dependency(self) -> None:
        """Verify the public feed API imports without loading Yahoo libraries."""

        self.assertIs(feed.DataFeed, DataFeed)
        self.assertIs(feed.YahooFeed, YahooFeed)
        self.assertIs(feed.TiingoFeed, TiingoFeed)
        self.assertIs(feed.Bar, Bar)
        self.assertIs(feed.OptionContract, OptionContract)
        self.assertIs(feed.OptionChain, OptionChain)
        self.assertIs(feed.OptionRight, OptionRight)
        self.assertNotIn("yfinance", sys.modules)

    def test_feed_imports_without_tiingo_token(self) -> None:
        """Verify importing feed does not require Tiingo credentials."""

        self.assertIs(feed.TiingoFeed, TiingoFeed)


class FeedModelTests(unittest.TestCase):
    def test_valid_bar_accepts_normalized_ohlcv_fields(self) -> None:
        """Verify a standard Bar can represent one provider-neutral OHLCV row."""

        bar = Bar(
            ticker="SPY",
            timestamp=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
            open="470.10",
            high="472.00",
            low="469.50",
            close="471.25",
            volume=1_000,
            interval="1m",
        )

        self.assertEqual(bar.ticker, "SPY")
        self.assertEqual(bar.close, Decimal("471.25"))
        self.assertEqual(bar.volume, Decimal("1000"))

    def test_bar_rejects_negative_volume_and_unknown_fields(self) -> None:
        """Verify Bar validation rejects invalid provider data before return."""

        valid_bar = {
            "ticker": "SPY",
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
            underlying_ticker="SPY",
            option_ticker="SPY240119C00470000",
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
            "underlying_ticker": "SPY",
            "option_ticker": "SPY240119P00470000",
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
            underlying_ticker="SPY",
            option_ticker="SPY240119C00470000",
            expiration=date(2024, 1, 19),
            strike="470",
            right="call",
        )
        put_contract = OptionContract(
            underlying_ticker="SPY",
            option_ticker="SPY240119P00470000",
            expiration=date(2024, 1, 19),
            strike="470",
            right="put",
        )

        chain = OptionChain(
            underlying_ticker="SPY",
            as_of=datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc),
            expiration=date(2024, 1, 19),
            contracts=[call_contract, put_contract],
        )

        self.assertEqual(chain.contracts, [call_contract, put_contract])
        self.assertEqual([contract.right for contract in chain.contracts], [OptionRight.CALL, OptionRight.PUT])


class DataFeedTests(unittest.IsolatedAsyncioTestCase):
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
            data_feed.get_current_bar("SPY"),
            data_feed.get_current_option_chain("SPY"),
            data_feed.get_historical_bars("SPY", date(2024, 1, 1), date(2024, 1, 2)),
            data_feed.get_historical_option_chain("SPY", date(2024, 1, 1)),
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

            async def get_current_bar(self, ticker: str, interval: str | None = None) -> Any:
                return {"ticker": ticker, "interval": interval}

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

        self.assertEqual(current_bar_hints["ticker"], str)
        self.assertEqual(current_chain_hints["ticker"], str)
        self.assertEqual(historical_bars_hints["ticker"], str)
        self.assertEqual(historical_chain_hints["ticker"], str)

    async def test_yahoo_feed_is_data_feed_and_keeps_historical_options_unsupported(self) -> None:
        """Verify YahooFeed implements only Yahoo-supported operations."""

        yahoo_feed = YahooFeed()

        self.assertIsInstance(yahoo_feed, DataFeed)
        self.assertTrue(yahoo_feed.supports("get_current_bar"))
        self.assertTrue(yahoo_feed.supports("get_historical_bars"))
        self.assertTrue(yahoo_feed.supports("get_current_option_chain"))
        self.assertFalse(yahoo_feed.supports("get_historical_option_chain"))
        with self.assertRaises(UnsupportedCapabilityError):
            await yahoo_feed.get_historical_option_chain("SPY", date(2024, 1, 1))


class FakeYahooClient:
    """Small fake matching the Yahoo client methods used by YahooFeed."""

    def __init__(self) -> None:
        self.history_calls: list[dict[str, Any]] = []
        self.option_chain_calls: list[str] = []
        self.options = ["2024-01-19"]
        self.history_data: Any = pd.DataFrame()
        self.option_chain_data: Any = SimpleNamespace(
            calls=pd.DataFrame(),
            puts=pd.DataFrame(),
        )

    def history(self, **kwargs: Any) -> Any:
        self.history_calls.append(kwargs)
        return self.history_data

    def option_chain(self, expiration: str) -> Any:
        self.option_chain_calls.append(expiration)
        return self.option_chain_data


class YahooFeedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = FakeYahooClient()
        self.requested_tickers: list[str] = []
        self.import_module = patch("feed.yahoo.importlib.import_module").start()
        self.import_module.return_value = SimpleNamespace(Ticker=self._ticker_factory)
        self.addCleanup(patch.stopall)
        self.yahoo_feed = YahooFeed()

    def _ticker_factory(self, ticker: str) -> FakeYahooClient:
        self.requested_tickers.append(ticker)
        return self.client

    async def test_current_bar_returns_standard_bar(self) -> None:
        """Verify Yahoo current data is normalized into a provider-neutral Bar."""

        self.client.history_data = pd.DataFrame(
            [{"Open": 470, "High": 472, "Low": 469, "Close": 471.25, "Volume": 1000}],
            index=pd.to_datetime(["2024-01-02T14:30:00Z"]),
        )

        bar = await self.yahoo_feed.get_current_bar(" SPY ", interval="1m")

        self.assertEqual(self.requested_tickers, ["SPY"])
        self.assertEqual(self.client.history_calls[0], {"period": "1d", "interval": "1m"})
        self.assertEqual(bar.ticker, "SPY")
        self.assertEqual(bar.close, Decimal("471.25"))
        self.assertEqual(bar.volume, Decimal("1000"))

    async def test_current_bar_raises_when_data_is_missing(self) -> None:
        """Verify Yahoo empty current data becomes DataUnavailableError."""

        with self.assertRaises(DataUnavailableError):
            await self.yahoo_feed.get_current_bar("SPY")

    async def test_historical_bars_return_standard_bar_list(self) -> None:
        """Verify Yahoo historical rows are normalized into list[Bar]."""

        self.client.history_data = pd.DataFrame(
            [
                {"Open": 470, "High": 472, "Low": 469, "Close": 471, "Volume": 1000},
                {"Open": 471, "High": 473, "Low": 470, "Close": 472, "Volume": 1200},
            ],
            index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
        )

        bars = await self.yahoo_feed.get_historical_bars(
            "ESZ5", date(2024, 1, 2), date(2024, 1, 4), interval="1d"
        )

        self.assertEqual(self.requested_tickers, ["ESZ5"])
        self.assertEqual(len(bars), 2)
        self.assertEqual([bar.ticker for bar in bars], ["ESZ5", "ESZ5"])
        self.assertEqual(bars[1].close, Decimal("472"))

    async def test_historical_bars_raise_when_empty(self) -> None:
        """Verify Yahoo empty historical data becomes DataUnavailableError."""

        with self.assertRaises(DataUnavailableError):
            await self.yahoo_feed.get_historical_bars("SPY", date(2024, 1, 2), date(2024, 1, 4))

    async def test_current_option_chain_preserves_calls_and_puts(self) -> None:
        """Verify Yahoo option rows become normalized call and put contracts."""

        self.client.option_chain_data = SimpleNamespace(
            calls=pd.DataFrame(
                [{"contractSymbol": "SPY240119C00470000", "strike": 470, "bid": 1.2, "ask": 1.25, "lastPrice": 1.22, "volume": 10, "openInterest": 250}]
            ),
            puts=pd.DataFrame(
                [{"contractSymbol": "SPY240119P00470000", "strike": 470, "bid": 1.1, "ask": 1.15, "lastPrice": 1.12, "volume": 8, "openInterest": 200}]
            ),
        )

        chain = await self.yahoo_feed.get_current_option_chain("SPY", expiration=date(2024, 1, 19))

        self.assertEqual(self.client.option_chain_calls, ["2024-01-19"])
        self.assertEqual(chain.underlying_ticker, "SPY")
        self.assertEqual(chain.expiration, date(2024, 1, 19))
        self.assertEqual([contract.right for contract in chain.contracts], [OptionRight.CALL, OptionRight.PUT])
        self.assertEqual(chain.contracts[0].option_ticker, "SPY240119C00470000")

    async def test_current_option_chain_uses_default_expiration(self) -> None:
        """Verify Yahoo default expiration is selected when caller omits one."""

        self.client.option_chain_data = SimpleNamespace(
            calls=pd.DataFrame([{"contractSymbol": "SPY240119C00470000", "strike": 470}]),
            puts=pd.DataFrame(),
        )

        chain = await self.yahoo_feed.get_current_option_chain("SPY")

        self.assertEqual(self.client.option_chain_calls, ["2024-01-19"])
        self.assertEqual(chain.expiration, date(2024, 1, 19))

    async def test_current_option_chain_raises_when_empty(self) -> None:
        """Verify Yahoo empty option-chain data becomes DataUnavailableError."""

        with self.assertRaises(DataUnavailableError):
            await self.yahoo_feed.get_current_option_chain("SPY", expiration=date(2024, 1, 19))

    async def test_non_empty_provider_ready_ticker_is_required(self) -> None:
        """Verify YahooFeed rejects blank tickers without provider mapping."""

        with self.assertRaises(MissingProviderMappingError):
            await self.yahoo_feed.get_current_bar("   ")

    async def test_missing_yahoo_dependency_is_normalized(self) -> None:
        """Verify missing yfinance import becomes a normalized feed error."""

        self.import_module.side_effect = ImportError("missing")

        with self.assertRaises(DataFeedError):
            await YahooFeed().get_current_bar("SPY")

    async def test_provider_exception_is_normalized(self) -> None:
        """Verify provider-native failures are mapped to normalized feed errors."""

        def failing_ticker(_: str) -> FakeYahooClient:
            raise RuntimeError("provider failed")

        self.import_module.return_value = SimpleNamespace(Ticker=failing_ticker)

        with self.assertRaises(NetworkError):
            await YahooFeed().get_current_bar("SPY")

    async def test_normalization_failure_is_normalized(self) -> None:
        """Verify malformed Yahoo numeric fields become NormalizationError."""

        self.client.history_data = pd.DataFrame(
            [{"Open": "bad", "High": 472, "Low": 469, "Close": 471, "Volume": 1000}],
            index=pd.to_datetime(["2024-01-02T14:30:00Z"]),
        )

        with self.assertRaises(NormalizationError):
            await self.yahoo_feed.get_current_bar("SPY")


class FakeTiingoResponse:
    """Small context-manager response matching urllib response behavior."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeTiingoResponse":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class FakeTiingoOpener:
    """Capture Tiingo requests and return configured fake payloads."""

    def __init__(self, payload: Any = None, exception: Exception | None = None) -> None:
        self.payload = payload if payload is not None else []
        self.exception = exception
        self.requests: list[Any] = []
        self.timeouts: list[float] = []

    def __call__(self, request: Any, *, timeout: float) -> FakeTiingoResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if self.exception is not None:
            raise self.exception
        return FakeTiingoResponse(self.payload)


class TiingoFeedTests(unittest.IsolatedAsyncioTestCase):
    def _feed(self, payload: Any = None, exception: Exception | None = None) -> tuple[TiingoFeed, FakeTiingoOpener]:
        opener = FakeTiingoOpener(payload=payload, exception=exception)
        return TiingoFeed(api_token="test-token", opener=opener), opener

    async def test_tiingo_feed_is_data_feed_and_keeps_options_unsupported(self) -> None:
        """Verify TiingoFeed implements only Tiingo-supported operations."""

        tiingo_feed = TiingoFeed(api_token="test-token", opener=FakeTiingoOpener())

        self.assertIsInstance(tiingo_feed, DataFeed)
        self.assertTrue(tiingo_feed.supports("get_current_bar"))
        self.assertTrue(tiingo_feed.supports("get_historical_bars"))
        self.assertFalse(tiingo_feed.supports("get_current_option_chain"))
        self.assertFalse(tiingo_feed.supports("get_historical_option_chain"))
        with self.assertRaises(UnsupportedCapabilityError):
            await tiingo_feed.get_current_option_chain("SPY")

    async def test_explicit_token_is_used_for_requests(self) -> None:
        """Verify explicit Tiingo tokens authenticate requests."""

        tiingo_feed, opener = self._feed([self._bar_payload("2024-01-02T00:00:00Z")])

        await tiingo_feed.get_current_bar("SPY")

        self.assertEqual(opener.requests[0].get_header("Authorization"), "Token test-token")

    def test_blank_constructor_token_raises_authentication_error(self) -> None:
        """Verify TiingoFeed requires an explicit non-empty constructor token."""

        with self.assertRaises(DataFeedAuthenticationError):
            TiingoFeed(api_token="   ", opener=FakeTiingoOpener())

    async def test_current_bar_returns_latest_standard_bar(self) -> None:
        """Verify Tiingo current bars use the newest available EOD row."""

        tiingo_feed, opener = self._feed(
            [
                self._bar_payload("2024-01-02T00:00:00Z", close=471),
                self._bar_payload("2024-01-03T00:00:00Z", close=472.5),
            ]
        )

        bar = await tiingo_feed.get_current_bar(" SPY ", interval="weekly")

        query = parse_qs(urlparse(opener.requests[0].full_url).query)
        self.assertEqual(query["resampleFreq"], ["weekly"])
        self.assertEqual(bar.ticker, "SPY")
        self.assertEqual(bar.close, Decimal("472.5"))
        self.assertEqual(bar.interval, "weekly")

    async def test_historical_bars_return_standard_bar_list_and_date_params(self) -> None:
        """Verify Tiingo historical rows and query bounds are normalized."""

        tiingo_feed, opener = self._feed(
            [
                self._bar_payload("2024-01-02T00:00:00Z", close=471),
                self._bar_payload("2024-01-03T00:00:00Z", close=472),
            ]
        )

        bars = await tiingo_feed.get_historical_bars(
            "SPY", date(2024, 1, 2), datetime(2024, 1, 4, tzinfo=timezone.utc)
        )

        query = parse_qs(urlparse(opener.requests[0].full_url).query)
        self.assertEqual(query["startDate"], ["2024-01-02"])
        self.assertEqual(query["endDate"], ["2024-01-04"])
        self.assertEqual(query["resampleFreq"], ["daily"])
        self.assertEqual(len(bars), 2)
        self.assertEqual([bar.close for bar in bars], [Decimal("471"), Decimal("472")])

    async def test_empty_and_missing_tiingo_payloads_are_unavailable(self) -> None:
        """Verify empty and incomplete Tiingo rows become unavailable data."""

        empty_feed, _ = self._feed([])
        with self.assertRaises(DataUnavailableError):
            await empty_feed.get_historical_bars("SPY", date(2024, 1, 2), date(2024, 1, 4))

        missing_feed, _ = self._feed([{"date": "2024-01-02T00:00:00Z", "open": 1}])
        with self.assertRaises(DataUnavailableError):
            await missing_feed.get_current_bar("SPY")

    async def test_malformed_tiingo_payloads_are_normalization_errors(self) -> None:
        """Verify malformed Tiingo payloads become normalized errors."""

        not_list_feed, _ = self._feed({"date": "2024-01-02T00:00:00Z"})
        with self.assertRaises(NormalizationError):
            await not_list_feed.get_current_bar("SPY")

        invalid_number_feed, _ = self._feed([self._bar_payload("2024-01-02T00:00:00Z", close="bad")])
        with self.assertRaises(NormalizationError):
            await invalid_number_feed.get_current_bar("SPY")

        invalid_json_feed, _ = self._feed(b"not-json")
        with self.assertRaises(NormalizationError):
            await invalid_json_feed.get_current_bar("SPY")

    async def test_http_statuses_are_normalized(self) -> None:
        """Verify Tiingo HTTP responses map to feed-layer errors."""

        cases = [
            (401, DataFeedAuthenticationError),
            (403, EntitlementError),
            (404, DataUnavailableError),
            (429, RateLimitError),
            (500, NetworkError),
        ]
        for status, expected_error in cases:
            with self.subTest(status=status):
                error = HTTPError("https://api.tiingo.test", status, "failed", hdrs=None, fp=None)
                tiingo_feed, _ = self._feed(exception=error)
                with self.assertRaises(expected_error):
                    await tiingo_feed.get_current_bar("SPY")

    async def test_network_and_timeout_errors_are_normalized(self) -> None:
        """Verify Tiingo network and timeout failures are normalized."""

        timeout_feed, _ = self._feed(exception=TimeoutError("slow"))
        with self.assertRaises(DataFeedTimeoutError):
            await timeout_feed.get_current_bar("SPY")

        url_timeout_feed, _ = self._feed(exception=URLError(TimeoutError("slow")))
        with self.assertRaises(DataFeedTimeoutError):
            await url_timeout_feed.get_current_bar("SPY")

        network_feed, _ = self._feed(exception=URLError("offline"))
        with self.assertRaises(NetworkError):
            await network_feed.get_current_bar("SPY")

    async def test_non_empty_provider_ready_ticker_is_required(self) -> None:
        """Verify TiingoFeed rejects blank tickers without provider mapping."""

        tiingo_feed, _ = self._feed([self._bar_payload("2024-01-02T00:00:00Z")])
        with self.assertRaises(MissingProviderMappingError):
            await tiingo_feed.get_current_bar("   ")

    @staticmethod
    def _bar_payload(value_date: str, close: Any = 471) -> dict[str, Any]:
        return {
            "date": value_date,
            "open": 470,
            "high": 472,
            "low": 469,
            "close": close,
            "volume": 1000,
        }


if __name__ == "__main__":
    unittest.main()