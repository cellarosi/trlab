"""
Base class for scheduled jobs.

Design Rationale:
- `BaseJob` acts as the fundamental contract for all tasks run by the `SchedulerEngine`.
- Utilizes `croniter` to dynamically calculate the next execution time based on 
  standard cron syntax (e.g., "*/6 * * * *"), ensuring robust and predictable 
  scheduling without complex external dependencies.
- Implements a "Log and Skip" resilience pattern: the infinite loop catches generic 
  `Exception` instances, logs them, and continues to the next scheduled run. This 
  ensures the perpetual nature of the job is maintained even during transient API 
  failures or network hiccups.
- Properly handles `asyncio.CancelledError` to allow the `SchedulerEngine` to 
  perform graceful shutdowns.
"""

import asyncio
import logging
from abc import ABC, abstractmethod

from croniter import croniter
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseJob(ABC):
    """Abstract base class defining the interface for all scheduled jobs."""

    def __init__(self, name: str, cron_schedule: str):
        self.name = name
        self.cron_schedule = cron_schedule

    @abstractmethod
    async def run_once(self) -> None:
        """Abstract method to be implemented by specific jobs. 
        Contains the core business logic for a single execution cycle."""
        pass

    async def start(self) -> None:
        """Infinite loop that calculates the next run time and sleeps until then.
        
        Execution Flow:
        1. Calculate `next_run` time from cron schedule.
        2. `asyncio.sleep` for the calculated duration.
        3. Execute `run_once()`.
        4. Wrap `run_once()` in `try...except Exception` to "Log and Skip" generic 
           errors, ensuring the job survives and restarts on the next cron cycle.
        5. Catch `asyncio.CancelledError` to re-raise and allow graceful termination 
           by the `SchedulerEngine`.
        """
        logger.info(f"Starting job: {self.name} with schedule: {self.cron_schedule}")
        try:
            while True:
                try:
                    now = datetime.now()
                    cron = croniter(self.cron_schedule, now)
                    next_run = cron.get_next(datetime)
                    sleep_duration = (next_run - now).total_seconds()
                    
                    if sleep_duration > 0:
                        logger.info(f"Job {self.name} sleeping for {sleep_duration:.2f} seconds until {next_run}")
                        await asyncio.sleep(sleep_duration)
                    
                    logger.info(f"Executing job: {self.name}")
                    await self.run_once()
                    
                except Exception as e:
                    # "Log and skip": catch the error, log it, and let the while loop continue.
                    # This is critical for the "perpetual" aspect of the download engine, 
                    # preventing a single failed fetch from stopping the entire scheduled task.
                    logger.error(f"Job {self.name} encountered an error: {e}. Skipping to next cycle.")
                    
        except asyncio.CancelledError:
            logger.info(f"Job {self.name} was cancelled.")
            raise