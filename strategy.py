import pandas as pd

REQUIRED_COLS = ['date', 'open', 'high', 'low', 'close']


def validate_bars(bars):
    if not isinstance(bars, pd.DataFrame):
        raise TypeError(f"bars must be a DataFrame, got {type(bars).__name__}")

    missing = set(REQUIRED_COLS) - set(bars.columns)
    if missing:
        raise ValueError(f"bars missing required columns: {missing}")

    for col in REQUIRED_COLS:
        if col == 'date':
            if not pd.api.types.is_datetime64_any_dtype(bars[col]):
                raise TypeError(f"Column 'date' must be datetime, got {bars[col].dtype}")
        else:
            if not pd.api.types.is_numeric_dtype(bars[col].dtype):
                raise TypeError(f"Column '{col}' must be numeric, got {bars[col].dtype}")


LONG = 1
SHORT = -1


class Strategy:
    max_concurrent_trade = 1

    def __init__(self):
        # bars[0] is the current bar; bars[1] is the previous, etc.
        self.bars = []
        self.trades = pd.DataFrame(columns=['side', 'entry_price', 'entry_time', 'exit_price', 'exit_time', 'pnl'])

    def on_bar(self, bar):
        pass

    def _open_position(self, direction):
        """Append a new open trade row."""
        price = self.bars[0].close
        row = pd.DataFrame([{
            'side': direction,
            'entry_price': price,
            'entry_time': self.bars[0].date,
            'exit_price': None,
            'exit_time': pd.NaT,
            'pnl': None,
        }])
        self.trades = pd.concat([self.trades, row], ignore_index=True)
        return self.trades.iloc[-1]

    def _close_position(self):
        """Fill exit fields on the oldest open trade and return it."""
        open_mask = self.trades['exit_price'].isna()
        idx = self.trades[open_mask].index[0]
        price = self.bars[0].close
        row = self.trades.loc[idx]
        pnl = self._pnl(row, price)
        self.trades.loc[idx, 'exit_price'] = price
        self.trades.loc[idx, 'exit_time'] = self.bars[0].date
        self.trades.loc[idx, 'pnl'] = pnl
        return self.trades.loc[idx]

    def _pnl(self, row, exit_price):
        if row['side'] == LONG:
            return exit_price - row['entry_price']
        return row['entry_price'] - exit_price

    def _close_opposite(self, direction):
        """Close oldest open trade if opposite direction. Returns True if open trades still remain."""
        open_mask = self.trades['exit_price'].isna()
        if open_mask.any() and self.trades[open_mask].iloc[0]['side'] != direction:
            row = self._close_position()
            label = 'CLOSE LONG' if row['side'] == LONG else 'CLOSE SHORT'
            print(f"{label} @ {row['exit_price']} (pnl={row['pnl']})")
            if self.trades['exit_price'].isna().any():
                return True
        return False

    def _try_open(self, direction):
        open_count = self.trades['exit_price'].isna().sum()
        if open_count < self.max_concurrent_trade:
            row = self._open_position(direction)
            label = 'BUY' if direction == LONG else 'SELL'
            print(f"{label} @ {row['entry_price']}")

    def buy(self):
        if self._close_opposite(LONG):
            return
        self._try_open(LONG)

    def sell(self):
        if self._close_opposite(SHORT):
            return
        self._try_open(SHORT)


class Backtest:

    def run(self, bars, strategy):
        validate_bars(bars)
        for _, bar in bars.iterrows():
            strategy.bars.insert(0, bar)
            strategy.on_bar(bar)


if __name__ == '__main__':
    df = pd.DataFrame({
        'date':  pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']),
        'open':  [100.0, 101.0, 102.0, 103.0, 104.0],
        'high':  [103.0, 104.0, 105.0, 106.0, 107.0],
        'low':   [99.0,  100.0, 101.0, 102.0, 103.0],
        'close': [102.0, 103.0, 104.0, 105.0, 106.0],
    })
    
    class PrintStrategy(Strategy):
        max_concurrent_trade = 2

        def on_bar(self, bar):
            n = len(self.bars)
            print(f"Bar {n}: {bar.date.date()}  O={bar.open} C={bar.close}")
            if n == 1:
                self.buy()
            elif n == 2:
                self.buy()       # stack another long (if max_concurrent > 1)
            elif n == 3:
                self.sell()       # close one long
            elif n == 4:
                self.sell()       # close remaining, flip to short
            elif n == 5:
                self.buy()        # close short, flip to long

    st = PrintStrategy()
    bt = Backtest()
    bt.run(df, st)
    print()
    closed = st.trades[st.trades['exit_price'].notna()]
    for _, t in closed.iterrows():
        print(f"CLOSED: {t.to_dict()}")
