"""
Core scheduler engine for managing multiple jobs.

Design Rationale:
- The `SchedulerEngine` acts as the orchestrator for all `BaseJob` instances.
- It uses `asyncio.gather` to run all jobs concurrently, allowing independent 
  cron schedules to operate without blocking each other.
- It maintains references to the running `asyncio.Task` objects, enabling 
  centralized, graceful cancellation and cleanup via the `stop()` method.
"""

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
        """Registers a job with the engine for future execution."""
        self._jobs.append(job)

    async def start(self) -> None:
        """Concurrently starts all registered jobs using asyncio.gather.
        
        Why asyncio.gather: It allows multiple perpetual jobs to run in the same 
        process without blocking each other. If one job's loop is awaiting, others 
        can still execute when their cron time arrives.
        """
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
        """Gracefully cancels all running job tasks.
        
        Invoked typically on KeyboardInterrupt or application shutdown to ensure 
        all child tasks are signaled to stop, triggering the CancelledError 
        handling in BaseJob.start().
        """
        logger.info("Stopping scheduler engine...")
        for task in self._tasks:
            if not task.done():
                task.cancel()