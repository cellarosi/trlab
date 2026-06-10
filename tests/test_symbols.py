"""Tests for symbol models and loading."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from symbols.models import InstrumentType, SessionDay, Sessions, Symbol, load_symbols


class SymbolTests(unittest.TestCase):
    def test_valid_entries(self) -> None:
        sessions = Sessions(
            timezone="America/New_York",
            monday=SessionDay(start="09:30", end="16:00"),
            tuesday=SessionDay(start="09:30", end="16:00"),
            wednesday=SessionDay(start="09:30", end="16:00"),
            thursday=SessionDay(start="09:30", end="16:00"),
            friday=SessionDay(start="09:30", end="16:00"),
            saturday=None,
            sunday=None,
        )
        entries = [
            Symbol(ticker="SPX", type="INDEX", contracts=[], sessions=sessions),
            Symbol(ticker="SPY", type="ETF", contracts=["SPY"], sessions=sessions),
            Symbol(ticker="ES", type="FUTURE", contracts=["ESZ5", "ESH6"], sessions=sessions),
            Symbol(ticker="SPY", type="OPTION", contracts=["SPY20260320"], sessions=sessions),
        ]

        self.assertEqual(entries[0].type, InstrumentType.INDEX)
        self.assertEqual(entries[1].contracts, ["SPY"])
        self.assertEqual(entries[2].contracts, ["ESZ5", "ESH6"])
        self.assertEqual(entries[3].contracts, ["SPY20260320"])

    def test_unsupported_instrument_type_is_rejected(self) -> None:
        sessions = Sessions(timezone="America/New_York")
        with self.assertRaises(ValidationError):
            Symbol(ticker="BTC", type="CRYPTO", contracts=[], sessions=sessions)

    def test_invalid_contracts_are_rejected(self) -> None:
        sessions = Sessions(timezone="America/New_York")
        invalid_contract_values = ["SPY", ["SPY", ""], ["SPY", "   "]]

        for contracts in invalid_contract_values:
            with self.subTest(contracts=contracts):
                with self.assertRaises(ValidationError):
                    Symbol(ticker="SPY", type="ETF", contracts=contracts, sessions=sessions)

    def test_empty_ticker_is_rejected(self) -> None:
        sessions = Sessions(timezone="America/New_York")
        with self.assertRaises(ValidationError):
            Symbol(ticker="   ", type="INDEX", contracts=[], sessions=sessions)

    def test_load_symbols_validates_all_entries(self) -> None:
        sessions = {
            "timezone": "America/New_York",
            "monday": {"start": "09:30", "end": "16:00"},
            "tuesday": {"start": "09:30", "end": "16:00"},
            "wednesday": {"start": "09:30", "end": "16:00"},
            "thursday": {"start": "09:30", "end": "16:00"},
            "friday": {"start": "09:30", "end": "16:00"},
            "saturday": None,
            "sunday": None,
        }
        symbols = [
            {"ticker": "SPX", "type": "INDEX", "contracts": [], "sessions": sessions},
            {"ticker": "ES", "type": "FUTURE", "contracts": ["ESZ5", "ESH6"], "sessions": sessions},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "symbols.json"
            path.write_text(json.dumps(symbols), encoding="utf-8")

            loaded = load_symbols(path)

        self.assertEqual([entry.ticker for entry in loaded], ["SPX", "ES"])
        self.assertEqual(loaded[1].type, InstrumentType.FUTURE)

    def test_load_symbols_fails_on_any_invalid_entry(self) -> None:
        sessions = {"timezone": "America/New_York"}
        symbols = [
            {"ticker": "SPX", "type": "INDEX", "contracts": [], "sessions": sessions},
            {"ticker": "BAD", "type": "UNKNOWN", "contracts": [], "sessions": sessions},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "symbols.json"
            path.write_text(json.dumps(symbols), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_symbols(path)

    def test_valid_sessions(self) -> None:
        sessions = Sessions(
            timezone="America/New_York",
            monday=SessionDay(start="09:30", end="16:00"),
            friday=SessionDay(start="09:30", end="16:00"),
        )
        symbol = Symbol(
            ticker="SPY",
            type="ETF",
            contracts=["SPY"],
            sessions=sessions,
        )
        self.assertEqual(symbol.sessions.timezone, "America/New_York")
        self.assertEqual(symbol.sessions.monday.start, "09:30")
        self.assertIsNone(symbol.sessions.saturday)

    def test_missing_timezone_raises_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            Sessions(monday=SessionDay(start="09:30", end="16:00"))

    def test_invalid_time_format_raises_validation_error(self) -> None:
        invalid_times = ["9:30", "16", "09:30:00", "9:30 AM"]
        for time_str in invalid_times:
            with self.subTest(time=time_str):
                with self.assertRaises(ValidationError):
                    SessionDay(start=time_str, end="16:00")


if __name__ == "__main__":
    unittest.main()