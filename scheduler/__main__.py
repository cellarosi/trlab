"""Entry point for the scheduler application."""

import argparse
import asyncio
import logging
from pathlib import Path

import yaml

from scheduler.core import SchedulerEngine
from scheduler.jobs.market_data_collector import MarketDataCollectorJob
from scheduler.models import SchedulerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> SchedulerConfig:
    """Load and parse the scheduler configuration from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)
    
    return SchedulerConfig.model_validate(raw_config)


def instantiate_jobs(config: SchedulerConfig) -> list:
    """Instantiate job classes based on the configuration."""
    jobs = []
    for job_cfg in config.jobs:
        if job_cfg.type == "market_data_collector":
            jobs.append(MarketDataCollectorJob(config=job_cfg.config))
        else:
            logger.warning(f"Unknown job type: {job_cfg.type}")
    return jobs


async def main() -> None:
    """Main entry point for the scheduler."""
    parser = argparse.ArgumentParser(description="Perpetual Async Scheduler")
    parser.add_argument(
        "-c", "--config",
        default="scheduler_config.yaml",
        help="Path to the configuration file (default: scheduler_config.yaml)"
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        print(config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    jobs = instantiate_jobs(config)
    if not jobs:
        logger.warning("No jobs configured. Exiting.")
        return

    engine = SchedulerEngine()
    for job in jobs:
        engine.add_job(job)

    logger.info("Starting scheduler engine...")
    try:
        await engine.start()
    except asyncio.CancelledError:
        logger.info("Scheduler engine cancelled.")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        engine.stop()
        logger.info("Scheduler engine stopped.")


if __name__ == "__main__":
    asyncio.run(main())