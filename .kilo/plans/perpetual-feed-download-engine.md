# Perpetual Async Scheduler App with Market Data Collector

## Overview
Implement a separate, extensible `scheduler` application/module. It will host a specific `market_data_collector` job that permanently downloads market data based on configurable cron-style schedules. The architecture will be designed to easily accommodate other types of scheduled jobs in the future.

## 1. Scheduler Core & Base Job (`scheduler/core.py`, `scheduler/jobs/base.py`)
- **`BaseJob`**: An abstract base class defining the interface for all scheduled jobs.
  - `name`: str
  - `cron_schedule`: str (e.g., "*/6 * * * *")
  - `async def run_once(self) -> None`: Abstract method to be implemented by specific jobs.
  - `async def start(self) -> None`: Infinite loop that calculates the next run time (e.g., using `croniter`), sleeps until then via `asyncio.sleep`, and then calls `run_once`. Wraps the loop body in a `try...except` block to implement "Log and Skip" for generic exceptions, ensuring the job survives transient errors. Handles graceful `asyncio.CancelledError` cancellation by re-raising.
- **`SchedulerEngine`**: Manages the lifecycle of multiple `BaseJob` instances.
  - `add_job(job: BaseJob)`: Registers a job.
  - `async start()`: Concurrently starts all registered jobs using `asyncio.gather`.
  - `stop()`: Gracefully cancels all running job tasks.

## 2. Market Data Collector Job (`scheduler/jobs/market_data_collector.py`)
- Inherits from `BaseJob`.
- Accepts a single `MarketDataCollectorConfig` instance (1:1 mapping with a YAML job entry).
- **`run_once` Implementation**:
  - **Provider Resolution**: Instantiates the appropriate `DataFeed` (e.g., `YahooFeed`) based on the `provider` string.
  - **Data Type Handling**:
    - For `bar`: Calls `get_current_bar`.
    - For `option_chain`: Since the requirement is "all expiration all strike", it will:
      1. Call `feed.get_option_expirations(symbol)` to retrieve the provider's list of available expirations via the `DataFeed` abstraction.
      2. Concurrently fetch all chains via `asyncio.gather` over the expirations, calling `get_current_option_chain` for each.
      3. Aggregate the results.
  - **Error Handling**: Wraps the entire execution in a `try...except` block. Logs exceptions using the standard `logging` module ("Log and Skip").
  - **Output**: Prints a concise summary to the console (e.g., `[2024-01-02 10:00:00] SUCCESS: SPY option_chain - 3 expirations, 450 contracts fetched`).

## 3. Configuration Models (`scheduler/models.py`)
- Define Pydantic models for strict, flat configuration parsing:
  - `DataType` enum: `bar`, `option_chain`
  - `MarketDataCollectorConfig`: `symbol` (str), `data_type` (DataType), `cron_schedule` (str), `provider` (str).
  - `JobConfig`: Base model with `type` (str, discriminator) and `config` (Union of specific job configs, e.g., `MarketDataCollectorConfig`).
  - `SchedulerConfig`: `jobs` (list[JobConfig]).
- This flat structure ensures a direct 1:1 mapping between a YAML job entry and a `BaseJob` instance, eliminating unnecessary nesting.
- Support loading configuration from `scheduler_config.yaml` or `scheduler_config.json`.
- *Note*: Requires adding `croniter` to `pyproject.toml` for robust cron schedule parsing and next-run calculation.

## 4. Entry Point (`scheduler/__main__.py`)
- A module-level entry point allowing the scheduler to be run directly via `python -m scheduler` or `python scheduler/main.py`.
- Logic:
  1. Accepts an optional config file path via command-line arguments (default: `scheduler_config.yaml` in the current working directory or a specified config path).
  2. Loads the configuration and instantiates the appropriate job classes based on `JobType`.
  3. Initializes `SchedulerEngine`, adds the jobs, and runs it via `asyncio.run()`.
  4. Handles `KeyboardInterrupt` to trigger graceful shutdown.

## 5. Example Configuration (`examples/scheduler_config.yaml`)
```yaml
jobs:
  - type: market_data_collector
    config:
      symbol: SPY
      data_type: option_chain
      provider: yahoo
      cron_schedule: "*/6 * * * *"  # Every 6 minutes
  - type: market_data_collector
    config:
      symbol: AAPL
      data_type: bar
      provider: yahoo
      cron_schedule: "0 * * * *"    # Every hour at minute 0
```

## Implementation Steps
1. Add `croniter` to `pyproject.toml` dependencies.
2. Create `scheduler/__init__.py`, `__main__.py`, `models.py`, `core.py`, and `scheduler/jobs/__init__.py`, `base.py`, `market_data_collector.py`.
3. Implement the Pydantic models and config loading logic with discriminated unions for extensibility.
4. Implement the `BaseJob` (with `croniter`-based sleep loop) and `SchedulerEngine` in `core.py`.
5. Implement the `MarketDataCollectorJob` with provider resolution, "all expirations" iteration, and error handling.
6. Add `examples/scheduler_config.yaml`.
7. Run type checking and linting to ensure compliance.
