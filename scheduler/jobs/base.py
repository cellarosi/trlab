"""Base class for scheduled jobs."""

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
        """Abstract method to be implemented by specific jobs."""
        pass

    async def start(self) -> None:
        """Infinite loop that calculates the next run time and sleeps until then."""
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
                    # "Log and skip": catch the error, log it, and let the while loop continue
                    logger.error(f"Job {self.name} encountered an error: {e}. Skipping to next cycle.")
                    
        except asyncio.CancelledError:
            logger.info(f"Job {self.name} was cancelled.")
            raise