import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from strategy import Backtest, Strategy, validate_bars, LONG, SHORT


def _make_df(**overrides):
    data = {
        'date':  pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
        'open':  [100.0, 101.0, 102.0],
        'high':  [103.0, 104.0, 105.0],
        'low':   [99.0,  100.0, 101.0],
        'close': [102.0, 103.0, 104.0],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def _push_bar(strategy, close, date=None):
    """Push a bar so buy/sell have self.bars[0] available."""
    if date is None:
        date = pd.Timestamp('2024-01-01')
    bar = pd.Series({'date': pd.Timestamp(date), 'open': close - 1, 'high': close + 1, 'low': close - 2, 'close': close})
    strategy.bars.insert(0, bar)


class ValidateBarsTest(unittest.TestCase):

    def test_valid_df_passes(self):
        df = _make_df()
        validate_bars(df)  # no raise

    def test_not_dataframe_raises(self):
        with self.assertRaises(TypeError):
            validate_bars([1, 2, 3])

    def test_missing_column_raises(self):
        df = _make_df()
        df = df.drop(columns=['close'])
        with self.assertRaises(ValueError):
            validate_bars(df)

    def test_non_numeric_ohlc_raises(self):
        df = _make_df(close=['a', 'b', 'c'])
        with self.assertRaises(TypeError):
            validate_bars(df)

    def test_non_datetime_date_raises(self):
        df = _make_df(date=[1, 2, 3])
        with self.assertRaises(TypeError):
            validate_bars(df)


class StrategyBarsTest(unittest.TestCase):

    def setUp(self):
        self.strategy = Strategy()

    def push_bars(self, n=3):
        for i in range(n):
            bar = pd.Series({
                'date': pd.Timestamp(f'2024-01-0{i+1}'),
                'open': float(100 + i),
                'high': float(103 + i),
                'low': float(99 + i),
                'close': float(102 + i),
            })
            self.strategy.bars.insert(0, bar)

    def test_bars_insert_order(self):
        self.push_bars(3)
        self.assertEqual(self.strategy.bars[0].close, 104.0)  # today
        self.assertEqual(self.strategy.bars[1].close, 103.0)  # yesterday
        self.assertEqual(self.strategy.bars[2].close, 102.0)  # two days ago

    def test_bars_length_grows(self):
        self.assertEqual(len(self.strategy.bars), 0)
        self.push_bars(1)
        self.assertEqual(len(self.strategy.bars), 1)
        self.push_bars(1)
        self.assertEqual(len(self.strategy.bars), 2)


class BacktestRunTest(unittest.TestCase):

    def test_iterates_all_rows_in_order(self):
        df = _make_df()

        class TrackStrategy(Strategy):
            def __init__(self):
                super().__init__()
                self.seen = []

            def on_bar(self, bar):
                self.seen.append(bar.close)

        s = TrackStrategy()
        Backtest().run(df, s)
        self.assertEqual(s.seen, [102.0, 103.0, 104.0])

    def test_bars_ordering_in_on_bar(self):
        df = _make_df()

        class OrderStrategy(Strategy):
            def __init__(self):
                super().__init__()
                self.record = []

            def on_bar(self, bar):
                n = len(self.bars)
                today = self.bars[0].close
                prev = self.bars[1].close if n > 1 else None
                self.record.append((today, prev))

        s = OrderStrategy()
        Backtest().run(df, s)
        self.assertEqual(s.record, [
            (102.0, None),
            (103.0, 102.0),
            (104.0, 103.0),
        ])

    def test_validation_runs_before_iteration(self):
        # on_bar should never be called if validation fails
        class NoCallStrategy(Strategy):
            def on_bar(self, bar):
                self.fail("on_bar should not be called for invalid data")

        s = NoCallStrategy()
        invalid = pd.DataFrame({'open': [1]})
        with self.assertRaises(ValueError):
            Backtest().run(invalid, s)


class StrategyTradeTest(unittest.TestCase):

    # -- helpers --

    def _open(self, s, i=0):
        """i-th open trade row."""
        return s.trades[s.trades['exit_price'].isna()].iloc[i]

    def _closed(self, s, i=0):
        """i-th closed trade row."""
        return s.trades[s.trades['exit_price'].notna()].iloc[i]

    # -- max_concurrent_trade=1 tests (default) --

    def test_buy_from_flat_opens_long(self):
        s = Strategy()
        _push_bar(s, 100)
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)
        row = self._open(s)
        self.assertEqual(row['side'], LONG)
        self.assertEqual(row['entry_price'], 100)

    def test_sell_from_flat_opens_short(self):
        s = Strategy()
        _push_bar(s, 100)
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)
        row = self._open(s)
        self.assertEqual(row['side'], SHORT)
        self.assertEqual(row['entry_price'], 100)

    def test_buy_when_short_flips_to_long(self):
        s = Strategy()
        _push_bar(s, 100, '2024-01-01')
        s.sell()
        _push_bar(s, 110, '2024-01-02')
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], LONG)
        self.assertEqual(row['entry_price'], 110)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)
        t = self._closed(s)
        self.assertEqual(t['side'], SHORT)
        self.assertEqual(t['entry_price'], 100)
        self.assertEqual(t['exit_price'], 110)
        self.assertEqual(t['pnl'], -10)

    def test_sell_when_long_flips_to_short(self):
        s = Strategy()
        _push_bar(s, 100, '2024-01-01')
        s.buy()
        _push_bar(s, 110, '2024-01-02')
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], SHORT)
        self.assertEqual(row['entry_price'], 110)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)
        t = self._closed(s)
        self.assertEqual(t['side'], LONG)
        self.assertEqual(t['entry_price'], 100)
        self.assertEqual(t['exit_price'], 110)
        self.assertEqual(t['pnl'], 10)

    def test_duplicate_buy_at_max_1_ignored(self):
        s = Strategy()
        _push_bar(s, 100)
        s.buy()
        _push_bar(s, 105)
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        self.assertEqual(self._open(s)['entry_price'], 100)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)

    def test_duplicate_sell_at_max_1_ignored(self):
        s = Strategy()
        _push_bar(s, 100)
        s.sell()
        _push_bar(s, 105)
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        self.assertEqual(self._open(s)['entry_price'], 100)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)

    # -- max_concurrent_trade > 1 tests --

    def test_stacks_longs_up_to_max(self):
        class S(Strategy):
            max_concurrent_trade = 3
        s = S()
        for price in [100, 101, 102, 103]:
            _push_bar(s, price)
            s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 3)
        self.assertEqual(self._open(s, 0)['entry_price'], 100)
        self.assertEqual(self._open(s, 1)['entry_price'], 101)
        self.assertEqual(self._open(s, 2)['entry_price'], 102)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)

    def test_stacks_shorts_up_to_max(self):
        class S(Strategy):
            max_concurrent_trade = 3
        s = S()
        for price in [100, 101, 102, 103]:
            _push_bar(s, price)
            s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 3)
        self.assertEqual(self._open(s, 0)['side'], SHORT)
        self.assertEqual(self._open(s, 0)['entry_price'], 100)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 0)

    def test_buy_closes_last_short_then_opens_long(self):
        class S(Strategy):
            max_concurrent_trade = 2
        s = S()
        for price in [100, 101]:
            _push_bar(s, price)
            s.sell()
        _push_bar(s, 95)
        s.buy()
        _push_bar(s, 90)
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], LONG)
        self.assertEqual(row['entry_price'], 90)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 2)

    def test_sell_closes_oldest_long_fifo(self):
        class S(Strategy):
            max_concurrent_trade = 3
        s = S()
        for price in [100, 101, 102]:
            _push_bar(s, price)
            s.buy()
        _push_bar(s, 110)
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 2)
        self.assertEqual(self._open(s, 0)['entry_price'], 101)
        self.assertEqual(self._open(s, 1)['entry_price'], 102)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)
        t = self._closed(s)
        self.assertEqual(t['entry_price'], 100)
        self.assertEqual(t['exit_price'], 110)
        self.assertEqual(t['pnl'], 10)

    def test_sell_while_longs_remain_does_not_open_short(self):
        class S(Strategy):
            max_concurrent_trade = 2
        s = S()
        for price in [100, 101]:
            _push_bar(s, price)
            s.buy()
        _push_bar(s, 105)
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], LONG)
        self.assertEqual(row['entry_price'], 101)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)

    def test_sell_closes_last_long_then_opens_short(self):
        class S(Strategy):
            max_concurrent_trade = 2
        s = S()
        for price in [100, 101]:
            _push_bar(s, price)
            s.buy()
        _push_bar(s, 105)
        s.sell()
        _push_bar(s, 110)
        s.sell()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], SHORT)
        self.assertEqual(row['entry_price'], 110)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 2)

    def test_buy_closes_oldest_short_fifo(self):
        class S(Strategy):
            max_concurrent_trade = 3
        s = S()
        for price in [100, 101, 102]:
            _push_bar(s, price)
            s.sell()
        _push_bar(s, 90)
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 2)
        self.assertEqual(self._open(s, 0)['entry_price'], 101)
        self.assertEqual(self._open(s, 1)['entry_price'], 102)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)
        t = self._closed(s)
        self.assertEqual(t['side'], SHORT)
        self.assertEqual(t['entry_price'], 100)
        self.assertEqual(t['exit_price'], 90)
        self.assertEqual(t['pnl'], 10)

    def test_buy_while_shorts_remain_does_not_open_long(self):
        class S(Strategy):
            max_concurrent_trade = 2
        s = S()
        for price in [100, 101]:
            _push_bar(s, price)
            s.sell()
        _push_bar(s, 95)
        s.buy()
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)
        row = self._open(s)
        self.assertEqual(row['side'], SHORT)
        self.assertEqual(s.trades['exit_price'].notna().sum(), 1)

    # -- Trade log fields --

    def test_trades_schema(self):
        s = Strategy()
        _push_bar(s, 100, '2024-01-01')
        s.buy()
        _push_bar(s, 110, '2024-01-02')
        s.sell()
        t = self._closed(s)
        self.assertEqual(set(t.index), {'side', 'entry_price', 'exit_price', 'entry_time', 'exit_time', 'pnl'})
        self.assertEqual(t['side'], LONG)
        self.assertEqual(t['entry_time'], pd.Timestamp('2024-01-01'))
        self.assertEqual(t['exit_time'], pd.Timestamp('2024-01-02'))
        # Open row has null exits, side is SHORT
        open_row = self._open(s)
        self.assertEqual(open_row['side'], SHORT)
        self.assertEqual(s.trades['exit_price'].isna().sum(), 1)


if __name__ == '__main__':
    unittest.main()
