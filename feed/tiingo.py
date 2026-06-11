"""Tiingo end-of-day market data feed adapter."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode, quote

import aiohttp

from feed.base import DataFeed, DateLike
from feed.errors import (
    DataFeedAuthenticationError,
    DataFeedError,
    DataFeedTimeoutError,
    DataUnavailableError,
    EntitlementError,
    MissingProviderMappingError,
    NetworkError,
    NormalizationError,
    RateLimitError,
)
from feed.models import Bar


class TiingoFeed(DataFeed):
    """Tiingo provider feed for authenticated end-of-day OHLCV bars."""

    _default_base_url = "https://api.tiingo.com"

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = _default_base_url,
        timeout: float = 30.0,
        client: aiohttp.ClientSession | None = None,
    ) -> None:
        self._api_token = api_token.strip()
        if not self._api_token:
            raise DataFeedAuthenticationError("Tiingo API token is required")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "TiingoFeed":
        if self._owns_client:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._client = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._owns_client and self._client is not None:
            await self._client.close()

    async def get_current_bar(self, ticker: str, interval: str | None = None) -> Bar:
        """Return the latest available Tiingo EOD bar as a standard Bar."""

        normalized_ticker = self._validate_ticker(ticker)
        rows = await self._request_prices(normalized_ticker, interval=interval)
        row = self._latest_row(rows, normalized_ticker)
        return self._bar_from_row(normalized_ticker, row, interval)

    async def get_historical_bars(
        self,
        ticker: str,
        start: DateLike,
        end: DateLike,
        interval: str | None = None,
    ) -> list[Bar]:
        """Return Tiingo historical EOD bars as standard Bar rows."""

        normalized_ticker = self._validate_ticker(ticker)
        rows = await self._request_prices(
            normalized_ticker,
            start=start,
            end=end,
            interval=interval,
        )
        if not rows:
            raise DataUnavailableError(f"No Tiingo historical bars for {normalized_ticker}")
        return [self._bar_from_row(normalized_ticker, row, interval) for row in rows]

    @classmethod
    def _validate_ticker(cls, ticker: str) -> str:
        """Normalize and reject blank provider-ready tickers."""

        normalized_ticker = ticker.strip()
        if not normalized_ticker:
            raise MissingProviderMappingError("ticker must be non-empty")
        return normalized_ticker

    async def _request_prices(
        self,
        ticker: str,
        *,
        start: DateLike | None = None,
        end: DateLike | None = None,
        interval: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch Tiingo EOD price rows for one ticker."""

        if self._client is None:
            raise NetworkError("Tiingo client is not initialized. Use 'async with' or provide a client.")
        
        params: dict[str, str] = {"resampleFreq": self._resample_frequency(interval)}
        if start is not None:
            params["startDate"] = self._date_param(start)
        if end is not None:
            params["endDate"] = self._date_param(end)
        url = self._prices_url(ticker, params)
        headers = {
            "Authorization": f"Token {self._api_token}",
            "Content-Type": "application/json",
        }
        payload = await self._request_json(url, headers)
        if not isinstance(payload, list):
            raise NormalizationError("Tiingo price payload must be a list")
        return [self._row_dict(row) for row in payload]

    def _prices_url(self, ticker: str, params: dict[str, str]) -> str:
        """Build a Tiingo historical prices endpoint URL."""

        encoded_ticker = quote(ticker, safe="")
        return f"{self._base_url}/tiingo/daily/{encoded_ticker}/prices?{urlencode(params)}"

    @staticmethod
    def _resample_frequency(interval: str | None) -> str:
        """Translate feed interval into Tiingo EOD resampling frequency."""

        return (interval or "daily").strip() or "daily"

    @staticmethod
    def _date_param(value: DateLike) -> str:
        """Format date-like values for Tiingo query parameters."""

        if isinstance(value, datetime):
            return value.date().isoformat()
        return value.isoformat()

    async def _request_json(self, url: str, headers: dict[str, str]) -> Any:
        """Run a Tiingo HTTP request and parse JSON with normalized errors."""

        if self._client is None:
            raise NetworkError("Tiingo client is not initialized. Use 'async with' or provide a client.")

        try:
            async with self._client.get(url, headers=headers) as response:
                if response.status >= 400:
                    raise self._error_for_status(response.status)
                text = await response.text()
                return json.loads(text)
        except DataFeedError:
            raise
        except asyncio.TimeoutError as exc:
            raise DataFeedTimeoutError("Tiingo provider request timed out") from exc
        except aiohttp.ClientError as exc:
            raise NetworkError("Tiingo provider request failed") from exc
        except json.JSONDecodeError as exc:
            raise NormalizationError("Tiingo provider returned invalid JSON") from exc
        except Exception as exc:
            raise NetworkError("Tiingo provider request failed") from exc

    @staticmethod
    def _error_for_status(status_code: int) -> DataFeedError:
        """Map Tiingo HTTP status codes to normalized feed errors."""

        if status_code == 401:
            return DataFeedAuthenticationError("Tiingo authentication failed")
        if status_code == 403:
            return EntitlementError("Tiingo entitlement denied")
        if status_code == 404:
            return DataUnavailableError("Tiingo data is unavailable")
        if status_code == 429:
            return RateLimitError("Tiingo rate limit exceeded")
        return NetworkError("Tiingo provider request failed")

    @staticmethod
    def _row_dict(row: Any) -> dict[str, Any]:
        """Return one Tiingo row as a dictionary or fail normalization."""

        if not isinstance(row, dict):
            raise NormalizationError("Tiingo price rows must be objects")
        return row

    def _latest_row(self, rows: list[dict[str, Any]], ticker: str) -> dict[str, Any]:
        """Select the newest Tiingo row by date for current-bar retrieval."""

        if not rows:
            raise DataUnavailableError(f"No Tiingo current bar data for {ticker}")
        try:
            return max(rows, key=lambda row: self._timestamp(row.get("date")))
        except DataFeedError:
            raise
        except Exception as exc:
            raise NormalizationError(f"Cannot normalize Tiingo current bar for {ticker}") from exc

    def _bar_from_row(self, ticker: str, row: dict[str, Any], interval: str | None) -> Bar:
        """Convert one Tiingo EOD row into the standard Bar model."""

        try:
            return Bar(
                ticker=ticker,
                timestamp=self._timestamp(self._required_value(row, "date")),
                open=self._required_decimal(row, "open"),
                high=self._required_decimal(row, "high"),
                low=self._required_decimal(row, "low"),
                close=self._required_decimal(row, "close"),
                volume=self._required_decimal(row, "volume"),
                interval=interval,
            )
        except DataFeedError:
            raise
        except Exception as exc:
            raise NormalizationError(f"Cannot normalize Tiingo bar for {ticker}") from exc

    @classmethod
    def _required_decimal(cls, row: dict[str, Any], name: str) -> Decimal:
        """Read a required Tiingo numeric field as Decimal."""

        value = cls._required_value(row, name)
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise NormalizationError(f"Invalid numeric Tiingo value for {name}") from exc

    @staticmethod
    def _required_value(row: dict[str, Any], name: str) -> Any:
        """Read a required Tiingo field."""

        value = row.get(name)
        if value is None or value != value:
            raise DataUnavailableError(f"Missing required Tiingo field: {name}")
        return value

    @staticmethod
    def _timestamp(value: Any) -> datetime:
        """Normalize Tiingo date strings into aware datetimes."""

        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
        text = str(value).replace("Z", "+00:00")
        try:
            timestamp = datetime.fromisoformat(text)
        except ValueError as exc:
            raise NormalizationError(f"Invalid Tiingo date value: {value!r}") from exc
        return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)