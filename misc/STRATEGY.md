# Strategy — Agent Session Handoff

## What this is

A minimal backtesting scaffold: a `Backtest` engine scrolls through a pandas DataFrame of OHLC bars and feeds them one-by-one to a `Strategy` class. Subclass `Strategy` and override `on_bar` to define trading logic. The strategy has access to all past bars via `self.bars`, indexed with `0` = current bar, `1` = previous bar, etc.

## Files

| File | Role |
|---|---|
| `strategy.py` | Core code — validation, strategy base class, backtest engine |
| `tests/test_strategy.py` | Unit tests — 10 tests, all passing |
| `misc/STRATEGY.md` | This document |

## How to run

```bash
# Smoke test
python3 strategy.py

# Tests
python3 -m unittest tests.test_strategy -v
```

## Architecture

### Data format

A pandas DataFrame with columns: `date` (datetime), `open`, `high`, `low`, `close` (numeric). Validated on every `Backtest.run()` call by `validate_bars()`.

### `validate_bars(bars)` — module-level function

Checks: is a DataFrame, has all required columns, `date` is datetime, OHLC are numeric. Raises `TypeError` or `ValueError` on failure.

No class — plain function, single purpose.

### `Strategy` — base class

```python
LONG = 1
SHORT = -1

class Strategy:
    max_concurrent_trade = 1    # override in subclass to change

    def __init__(self):
        self.bars = []           # bars[0] = current bar, bars[1] = previous
        self.trades = pd.DataFrame(columns=[
            'side', 'entry_price', 'entry_time',
            'exit_price', 'exit_time', 'pnl',
        ])
        # Open trades have exit_price/exit_time/pnl = null.
        # side uses LONG/SHORT constants, not strings.

    def on_bar(self, bar):
        pass

    def buy(self):
        # Closes oldest short if short; if more shorts remain, stops.
        # Otherwise opens a long if under max_concurrent_trade.
        pass

    def sell(self):
        # Closes oldest long if long; if more longs remain, stops.
        # Otherwise opens a short if under max_concurrent_trade.
        pass
```

Key design decisions:

- **`self.bars` is prepended, NOT appended**. `Backtest.run` uses `insert(0, bar)` so `bars[0]` is always the current bar and `bars[n]` is n bars ago.
- **Single DataFrame `self.trades`** — no separate lists. Open trades have null `exit_price`/`exit_time`/`pnl`; closed trades have all fields filled.
- **`side` uses `LONG=1`/`SHORT=-1` constants**, not strings. No mapping needed.
- **`buy()`/`sell()` always use `self.bars[0].close`** — no parameters.
- **Opposing signals close positions (FIFO)**. `buy()` closes the oldest short; `sell()` closes the oldest long. If positions remain after closing one, direction does NOT flip.
- **Same-direction signals at max are ignored**. With `max_concurrent_trade=3`, a 4th `buy()` is a no-op.
- **Positions are one-directional**. You're either long, short, or flat — never mixed.
- **PnL**: long = `exit - entry`, short = `entry - exit`.
- **`max_concurrent_trade` is a class attribute**, not a constructor parameter. Subclasses override it:
  ```python
  class MyStrategy(Strategy):
      max_concurrent_trade = 3
  ```

### `Backtest` — engine

```python
class Backtest:
    def run(self, bars, strategy):
        validate_bars(bars)
        for _, bar in bars.iterrows():
            strategy.bars.insert(0, bar)
            strategy.on_bar(bar)
```

Takes a DataFrame and a Strategy, validates, then iterates row-by-row. No state of its own — purely a loop.

## Design decisions

- **`bars[0]` = today via `insert(0)`.** Cleaner than negative indexing for a rolling window where "today" should always be the first index.
- **No Data/DataValidator classes.** Started with them, reverted to a plain function. A class with one method is a function.
- **Validation runs inside `Backtest.run`.** No separate wiring needed — the engine owns the contract.
- **`buy()`/`sell()` always use close price.** No price parameter — always `self.bars[0].close`.
- **Opposing signals close one position (FIFO), same signals stack.** A `sell` against 3 longs closes the oldest; 2 remain, no short opened. A `buy` at max is ignored.
- **`max_concurrent_trade` is a class attribute.** Subclasses set it directly — no constructor plumbing.

## What's not done

- No stop-loss, take-profit, or order types
- No multi-asset support
- No performance metrics (Sharpe, drawdown, etc.)
- No bar API abstraction — `on_bar` receives a pandas Series

## Test suite

25 tests in 4 classes:

| Class | Tests | Coverage |
|---|---|---|
| `ValidateBarsTest` | 5 | Valid df passes; non-df, missing col, non-numeric, non-datetime all raise |
| `StrategyBarsTest` | 2 | `bars[0]`/`[1]`/`[2]` ordering after `insert(0)`, length grows correctly |
| `BacktestRunTest` | 3 | Iterates all rows in order, `self.bars` ordering during `on_bar`, validation blocks bad data before iteration |
| `StrategyTradeTest` | 15 | buy/sell from flat, flip on opposite signal, FIFO closing, stacking up to max, duplicate ignore, short-side mirrors, trade log fields |

## Future directions

- Add size parameter to `buy()`/`sell()` so each signal can open/close a specific quantity
- Add an `OrderManager` that translates buy/sell signals into positions, tracking size and P&L
- Add `on_start` and `on_finish` lifecycle hooks to Strategy
- Support bar indexing beyond the simple `insert(0)` pattern (e.g., time-based lookback via `self.bars` filtered by date)
- Add a `Broker` abstraction for execution simulation (slippage, commissions)
