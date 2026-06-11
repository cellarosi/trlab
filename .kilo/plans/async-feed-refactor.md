# Plan: Refactor Feed Classes to True Async Coroutines

## Objective
Refactor `YahooFeed` and `TiingoFeed` to eliminate synchronous blocking I/O, ensuring they function as true asynchronous coroutines that do not starve the Python `asyncio` event loop.

## Current State Analysis
- **`YahooFeed`**: Methods are marked `async def`, but they invoke `yfinance` methods (which use synchronous HTTP requests under the hood) via a synchronous lambda in `_call_provider`. This blocks the event loop.
- **`TiingoFeed`**: Methods are marked `async def`, but they invoke `urllib.request.urlopen`, which is a blocking, synchronous network call. This also blocks the event loop.

## Proposed Solution

### 1. Dependency Update
- Add `aiohttp` to `dependencies` in `pyproject.toml`. `aiohttp` is a fully async-compatible HTTP client that will replace `urllib` for `TiingoFeed`.

### 2. Refactor `YahooFeed` (Option A: Thread Pool Offloading)
- Since `yfinance` is inherently synchronous, replacing it is out of scope and fragile.
- Use `asyncio.to_thread` to offload the blocking `yfinance` execution to a background worker thread.
- **Action**: Modify `_call_provider` to be an `async def` method that uses `await asyncio.to_thread(call)`. 
- **Result**: The event loop remains unblocked while `yfinance` performs its synchronous HTTP requests. Existing error handling in `_call_provider` is preserved.

### 3. Refactor `TiingoFeed` (Option B: Native Async HTTP)
- Replace the synchronous `urllib.request` stack with `aiohttp.ClientSession`.
- **Action 1**: Update `TiingoFeed.__init__` to accept an optional `aiohttp.ClientSession` instance (for dependency injection/testing), defaulting to `None`.
- **Action 2**: Convert `_request_json` to `async def _request_json` and use `async with self._client.get(url, headers=headers) as response:`.
- **Action 3**: Convert `_request_prices` to `async def _request_prices` and `await` the call to `_request_json`.
- **Action 4**: Update `get_current_bar` and `get_historical_bars` to `await` the newly asynchronous `_request_prices`.
- **Action 5**: Implement `__aenter__` and `__aexit__` on `TiingoFeed` to cleanly close the internally created `aiohttp.ClientSession` and prevent resource leaks, enabling `async with TiingoFeed(...) as feed:` usage.

### 4. Validation
- Run dependency installation (e.g., `poetry install`).
- Run `mypy feed/` to ensure type hints are correct, especially around the new `aiohttp` types and `asyncio` returns.
- Run `ruff check feed/` to ensure code style compliance.

## Trade-offs & Considerations
- **YahooFeed Concurrency**: `asyncio.to_thread` uses the default thread pool executor. Under extreme concurrent load, this could exhaust threads, but it is the standard and safest approach for wrapping synchronous third-party libraries like `yfinance`.
- **TiingoFeed Resource Management**: Introducing `httpx.AsyncClient` requires proper lifecycle management. Adding `__aenter__`/`__aexit__` allows users to cleanly manage connection pooling and closure.

## Decisions Confirmed
- `httpx` will be added as a project dependency.
- `TiingoFeed` will handle lazy internal creation of its own `httpx.AsyncClient` and provide `__aenter__`/`__aexit__` for context manager support (`async with TiingoFeed(...) as feed:`).
