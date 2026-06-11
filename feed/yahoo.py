"""Yahoo market data feed adapter."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from feed.base import DataFeed
from feed.errors import (
    DataFeedError,
    DataFeedTimeoutError,
    DataUnavailableError,
    MissingProviderMappingError,
    NetworkError,
    NormalizationError,
)
from feed.models import Bar, OptionChain, OptionContract, OptionRight


class YahooFeed(DataFeed):
    """Yahoo provider feed for provider-ready ticker strings."""

    async def get_current_bar(self, ticker: str, interval: str | None = None) -> Bar:
        """Return Yahoo delayed/current bar data as a standard Bar."""

        normalized_ticker = self._validate_ticker(ticker)
        client = self._client_for(normalized_ticker)
        data = self._call_provider(
            lambda: client.history(period="1d", interval=interval or "1d")
        )
        row, timestamp = self._latest_row(data, normalized_ticker)
        return self._bar_from_row(normalized_ticker, row, timestamp, interval)

    async def get_current_option_chain(
        self, ticker: str, expiration: date | None = None
    ) -> OptionChain:
        """Return Yahoo current option-chain data as a standard OptionChain."""

        normalized_ticker = self._validate_ticker(ticker)
        client = self._client_for(normalized_ticker)
        selected_expiration = self._resolve_option_expiration(client, expiration)
        data = self._call_provider(
            lambda: client.option_chain(selected_expiration.isoformat())
        )
        contracts = [
            *self._option_contracts_from_rows(
                normalized_ticker, selected_expiration, getattr(data, "calls", None), OptionRight.CALL
            ),
            *self._option_contracts_from_rows(
                normalized_ticker, selected_expiration, getattr(data, "puts", None), OptionRight.PUT
            ),
        ]
        if not contracts:
            raise DataUnavailableError(f"No Yahoo option-chain data for {normalized_ticker}")
        return OptionChain(
            underlying_ticker=normalized_ticker,
            as_of=datetime.now(timezone.utc),
            expiration=selected_expiration,
            contracts=contracts,
        )

    async def get_historical_bars(
        self,
        ticker: str,
        start: date | datetime,
        end: date | datetime,
        interval: str | None = None,
    ) -> list[Bar]:
        """Return Yahoo historical bars as standard Bar rows."""

        normalized_ticker = self._validate_ticker(ticker)
        client = self._client_for(normalized_ticker)
        data = self._call_provider(
            lambda: client.history(start=start, end=end, interval=interval or "1d")
        )
        if self._is_empty(data):
            raise DataUnavailableError(f"No Yahoo historical bars for {normalized_ticker}")
        return [
            self._bar_from_row(normalized_ticker, row, timestamp, interval)
            for timestamp, row in self._iter_rows(data)
        ]

    async def get_option_expirations(self, ticker: str) -> list[date]:
        """Return the list of available Yahoo option expiration dates for a ticker."""
        normalized_ticker = self._validate_ticker(ticker)
        client = self._client_for(normalized_ticker)
        options = self._call_provider(lambda: getattr(client, "options", None))
        
        if not options:
            raise DataUnavailableError(f"No Yahoo option expirations available for {normalized_ticker}")
            
        return [self._parse_date(exp) for exp in options]

    @staticmethod
    def _validate_ticker(ticker: str) -> str:
        """Normalize and reject blank provider-ready tickers."""

        normalized_ticker = ticker.strip()
        if not normalized_ticker:
            raise MissingProviderMappingError("ticker must be non-empty")
        return normalized_ticker

    def _client_for(self, ticker: str) -> Any:
        """Create the Yahoo client lazily so importing feed stays provider-light."""

        try:
            yf = importlib.import_module("yfinance")
        except ImportError as exc:
            raise DataFeedError("Yahoo provider dependency is not installed") from exc
        return self._call_provider(lambda: yf.Ticker(ticker))

    @staticmethod
    def _call_provider(call: Callable[[], Any]) -> Any:
        """Run a Yahoo call and expose only normalized feed-layer errors."""

        try:
            return call()
        except TimeoutError as exc:
            raise DataFeedTimeoutError("Yahoo provider request timed out") from exc
        except DataFeedError:
            raise
        except Exception as exc:
            raise NetworkError("Yahoo provider request failed") from exc

    @staticmethod
    def _is_empty(data: Any) -> bool:
        """Return whether Yahoo returned no usable rows or payload."""

        if data is None:
            return True
        empty = getattr(data, "empty", None)
        if empty is not None:
            return bool(empty)
        try:
            return len(data) == 0
        except TypeError:
            return False

    def _latest_row(self, data: Any, ticker: str) -> tuple[Any, Any]:
        """Extract the latest Yahoo history row for current-bar normalization."""

        if self._is_empty(data):
            raise DataUnavailableError(f"No Yahoo current bar data for {ticker}")
        try:
            row = data.iloc[-1]
            return row, getattr(row, "name", None)
        except AttributeError:
            rows = list(self._iter_rows(data))
            if not rows:
                raise DataUnavailableError(f"No Yahoo current bar data for {ticker}")
            timestamp, row = rows[-1]
            return row, timestamp
        except Exception as exc:
            raise NormalizationError(f"Cannot normalize Yahoo current bar for {ticker}") from exc

    @staticmethod
    def _iter_rows(data: Any) -> Iterable[tuple[Any, Any]]:
        """Yield timestamp and row pairs from dataframe, dict, or iterable data."""

        if hasattr(data, "iterrows"):
            yield from data.iterrows()
            return
        if isinstance(data, dict):
            yield None, data
            return
        for row in data:
            yield None, row

    def _bar_from_row(
        self, ticker: str, row: Any, timestamp: Any, interval: str | None
    ) -> Bar:
        """Convert one Yahoo OHLCV row into the standard Bar model."""

        try:
            return Bar(
                ticker=ticker,
                timestamp=self._timestamp_or_now(timestamp),
                open=self._required_decimal(row, "Open", "open"),
                high=self._required_decimal(row, "High", "high"),
                low=self._required_decimal(row, "Low", "low"),
                close=self._required_decimal(row, "Close", "close"),
                volume=self._required_decimal(row, "Volume", "volume"),
                interval=interval,
            )
        except DataFeedError:
            raise
        except Exception as exc:
            raise NormalizationError(f"Cannot normalize Yahoo bar for {ticker}") from exc

    def _resolve_option_expiration(self, client: Any, expiration: date | None) -> date:
        """Use the requested option expiration or Yahoo's first available one."""

        if expiration is not None:
            return expiration
        options = self._call_provider(lambda: getattr(client, "options", None))
        if not options:
            raise DataUnavailableError("No Yahoo option expirations are available")
        return self._parse_date(options[0])

    def _option_contracts_from_rows(
        self,
        underlying_ticker: str,
        expiration: date,
        rows: Any,
        right: OptionRight,
    ) -> list[OptionContract]:
        """Convert Yahoo call or put rows into standard option contracts."""

        if self._is_empty(rows):
            return []
        return [
            self._option_contract_from_row(underlying_ticker, expiration, row, right)
            for _, row in self._iter_rows(rows)
        ]

    def _option_contract_from_row(
        self,
        underlying_ticker: str,
        expiration: date,
        row: Any,
        right: OptionRight,
    ) -> OptionContract:
        """Convert one Yahoo option row into the standard OptionContract model."""

        try:
            return OptionContract(
                underlying_ticker=underlying_ticker,
                option_ticker=self._required_value(row, "contractSymbol", "option_ticker"),
                expiration=expiration,
                strike=self._required_decimal(row, "strike", "Strike"),
                right=right,
                bid=self._optional_decimal(row, "bid", "Bid"),
                ask=self._optional_decimal(row, "ask", "Ask"),
                last=self._optional_decimal(row, "lastPrice", "last", "Last"),
                volume=self._optional_int(row, "volume", "Volume"),
                open_interest=self._optional_int(row, "openInterest", "open_interest"),
            )
        except DataFeedError:
            raise
        except Exception as exc:
            raise NormalizationError(
                f"Cannot normalize Yahoo option contract for {underlying_ticker}"
            ) from exc

    @classmethod
    def _required_decimal(cls, row: Any, *names: str) -> Decimal:
        """Read a required Yahoo numeric field as Decimal."""

        value = cls._required_value(row, *names)
        return cls._to_decimal(value)

    @classmethod
    def _optional_decimal(cls, row: Any, *names: str) -> Decimal | None:
        """Read an optional Yahoo numeric field as Decimal when present."""

        value = cls._value(row, *names)
        if cls._is_missing(value):
            return None
        return cls._to_decimal(value)

    @classmethod
    def _optional_int(cls, row: Any, *names: str) -> int | None:
        """Read an optional Yahoo numeric field as int when present."""

        value = cls._value(row, *names)
        if cls._is_missing(value):
            return None
        return int(value)

    @classmethod
    def _required_value(cls, row: Any, *names: str) -> Any:
        """Read a required Yahoo field, accepting alternate field names."""

        value = cls._value(row, *names)
        if cls._is_missing(value):
            raise DataUnavailableError(f"Missing required Yahoo field: {names[0]}")
        return value

    @staticmethod
    def _value(row: Any, *names: str) -> Any:
        """Read the first available field name from a Yahoo row-like object."""

        for name in names:
            if hasattr(row, "get"):
                value = row.get(name)
                if value is not None:
                    return value
            elif isinstance(row, dict) and name in row:
                return row[name]
        return None

    @classmethod
    def _to_decimal(cls, value: Any) -> Decimal:
        """Convert provider numeric values to Decimal for public models."""

        if cls._is_missing(value):
            raise DataUnavailableError("Missing numeric Yahoo value")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise NormalizationError(f"Invalid numeric Yahoo value: {value!r}") from exc

    @staticmethod
    def _is_missing(value: Any) -> bool:
        """Return true for missing values including NaN-like values."""

        return value is None or value != value

    @staticmethod
    def _timestamp_or_now(value: Any) -> datetime:
        """Normalize Yahoo row timestamps, falling back to current UTC time."""

        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        try:
            timestamp = value.to_pydatetime()
        except AttributeError:
            return datetime.now(timezone.utc)
        return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

    @staticmethod
    def _parse_date(value: Any) -> date:
        """Normalize Yahoo expiration values into date objects."""

        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise NormalizationError(f"Invalid Yahoo option expiration: {value!r}") from exc