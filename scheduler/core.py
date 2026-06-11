"""Core scheduler engine for managing multiple jobs."""

import asyncio
import logging
from typing import List

from scheduler.jobs.base import BaseJob

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """Manages the lifecycle of multiple BaseJob instances."""

    def __init__(self):
        self._jobs: List[BaseJob] = []
        self._tasks: List[asyncio.Task] = []

    def add_job(self, job: BaseJob) -> None:
        """Registers a job."""
        self._jobs.append(job)

    async def start(self) -> None:
        """Concurrently starts all registered jobs using asyncio.gather."""
        if not self._jobs:
            logger.warning("No jobs to start.")
            return
        
        logger.info(f"Starting {len(self._jobs)} jobs...")
        self._tasks = [asyncio.create_task(job.start()) for job in self._jobs]
        
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("Scheduler engine tasks were cancelled.")
            raise

    def stop(self) -> None:
        """Gracefully cancels all running job tasks."""
        logger.info("Stopping scheduler engine...")
        for task in self._tasks:
            if not task.done():
                task.cancel()