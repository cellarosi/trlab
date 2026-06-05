"""Tests for symbol models and loading."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from symbols.models import InstrumentType, Symbol, load_symbols


class SymbolTests(unittest.TestCase):
    def test_valid_entries(self) -> None:
        entries = [
            Symbol(ticker="SPX", type="INDEX", contracts=[]),
            Symbol(ticker="SPY", type="ETF", contracts=["SPY"]),
            Symbol(ticker="ES", type="FUTURE", contracts=["ESZ5", "ESH6"]),
            Symbol(ticker="SPY", type="OPTION", contracts=["SPY20260320"]),
        ]

        self.assertEqual(entries[0].type, InstrumentType.INDEX)
        self.assertEqual(entries[1].contracts, ["SPY"])
        self.assertEqual(entries[2].contracts, ["ESZ5", "ESH6"])
        self.assertEqual(entries[3].contracts, ["SPY20260320"])

    def test_unsupported_instrument_type_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Symbol(ticker="BTC", type="CRYPTO", contracts=[])

    def test_invalid_contracts_are_rejected(self) -> None:
        invalid_contract_values = ["SPY", ["SPY", ""], ["SPY", "   "]]

        for contracts in invalid_contract_values:
            with self.subTest(contracts=contracts):
                with self.assertRaises(ValidationError):
                    Symbol(ticker="SPY", type="ETF", contracts=contracts)

    def test_empty_ticker_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Symbol(ticker="   ", type="INDEX", contracts=[])

    def test_load_symbols_validates_all_entries(self) -> None:
        symbols = [
            {"ticker": "SPX", "type": "INDEX", "contracts": []},
            {"ticker": "ES", "type": "FUTURE", "contracts": ["ESZ5", "ESH6"]},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "symbols.json"
            path.write_text(json.dumps(symbols), encoding="utf-8")

            loaded = load_symbols(path)

        self.assertEqual([entry.ticker for entry in loaded], ["SPX", "ES"])
        self.assertEqual(loaded[1].type, InstrumentType.FUTURE)

    def test_load_symbols_fails_on_any_invalid_entry(self) -> None:
        symbols = [
            {"ticker": "SPX", "type": "INDEX", "contracts": []},
            {"ticker": "BAD", "type": "UNKNOWN", "contracts": []},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "symbols.json"
            path.write_text(json.dumps(symbols), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_symbols(path)


if __name__ == "__main__":
    unittest.main()
