"""Tests for the scheduler module."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from scheduler.core import SchedulerEngine
from scheduler.jobs.base import BaseJob
from scheduler.jobs.market_data_collector import MarketDataCollectorJob
from scheduler.models import DataType, MarketDataCollectorConfig, SchedulerConfig
from feed.models import OptionChain


class MockJob(BaseJob):
    """Concrete implementation of BaseJob for testing."""

    def __init__(self, name: str, cron_schedule: str):
        super().__init__(name, cron_schedule)
        self.run_once_mock = AsyncMock()

    async def run_once(self) -> None:
        await self.run_once_mock()


class SchedulerModelsTests(unittest.TestCase):
    def test_valid_scheduler_config(self) -> None:
        """Test that a valid scheduler configuration is parsed correctly with discriminated unions."""
        config_data = {
            "jobs": [
                {
                    "type": "market_data_collector",
                    "config": {
                        "symbol": "SPY",
                        "data_type": "option_chain",
                        "cron_schedule": "*/5 * * * *",
                        "provider": "yahoo",
                    },
                }
            ]
        }
        config = SchedulerConfig.model_validate(config_data)
        self.assertEqual(len(config.jobs), 1)
        job_config = config.jobs[0]
        self.assertEqual(job_config.type, "market_data_collector")
        self.assertEqual(job_config.config.symbol, "SPY")
        self.assertEqual(job_config.config.data_type, DataType.OPTION_CHAIN)

    def test_invalid_job_type_raises_validation_error(self) -> None:
        """Test that an unknown job type raises a Pydantic ValidationError."""
        config_data = {
            "jobs": [
                {
                    "type": "unknown_job",
                    "config": {"symbol": "SPY"},
                }
            ]
        }
        with self.assertRaises(ValidationError):
            SchedulerConfig.model_validate(config_data)

    def test_missing_required_fields_raises_validation_error(self) -> None:
        """Test that missing required fields in job config raises a ValidationError."""
        config_data = {
            "jobs": [
                {
                    "type": "market_data_collector",
                    "config": {
                        "data_type": "bar",
                        "cron_schedule": "* * * * *",
                        "provider": "yahoo",
                    },
                }
            ]
        }
        with self.assertRaises(ValidationError):
            SchedulerConfig.model_validate(config_data)


class BaseJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_base_job_start_executes_run_once(self) -> None:
        """Test that BaseJob.start() calculates sleep time, sleeps, and executes run_once()."""
        job = MockJob(name="test_job", cron_schedule="* * * * *")

        # Mock croniter to return a time in the past so sleep_duration <= 0 and it executes immediately
        with patch("scheduler.jobs.base.croniter") as mock_croniter_class:
            mock_cron = MagicMock()
            # Return a time in the past relative to datetime.now()
            mock_cron.get_next.return_value = datetime(2020, 1, 1, 0, 0, 0)
            mock_croniter_class.return_value = mock_cron

            # Make run_once raise CancelledError after the first call to break the loop
            job.run_once_mock.side_effect = [None, asyncio.CancelledError()]

            with patch("scheduler.jobs.base.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                try:
                    await job.start()
                except asyncio.CancelledError:
                    pass

                job.run_once_mock.assert_called()
                # sleep should NOT be called because sleep_duration <= 0
                mock_sleep.assert_not_called()

    async def test_base_job_start_logs_and_skips_exceptions(self) -> None:
        """Test that BaseJob.start() catches exceptions in run_once(), logs them, and continues."""
        job = MockJob(name="test_job", cron_schedule="* * * * *")
        
        with patch("scheduler.jobs.base.croniter") as mock_croniter_class:
            mock_cron = MagicMock()
            mock_cron.get_next.return_value = datetime(2020, 1, 1, 0, 0, 0)
            mock_croniter_class.return_value = mock_cron

            # Fail on first call, succeed on second, then cancel on third to break the loop
            job.run_once_mock.side_effect = [RuntimeError("Test error"), None, asyncio.CancelledError()]

            with patch("scheduler.jobs.base.asyncio.sleep", new_callable=AsyncMock):
                with patch("scheduler.jobs.base.logger.error") as mock_logger_error:
                    try:
                        await job.start()
                    except asyncio.CancelledError:
                        pass

                    # Called 3 times: 1st (error), 2nd (success), 3rd (CancelledError)
                    self.assertEqual(job.run_once_mock.call_count, 3)
                    mock_logger_error.assert_called_once()
                    self.assertIn("Test error", mock_logger_error.call_args[0][0])


class SchedulerEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_engine_starts_and_stops_jobs(self) -> None:
        """Test that SchedulerEngine concurrently starts jobs and gracefully stops them."""
        engine = SchedulerEngine()
        job1 = MockJob(name="job1", cron_schedule="* * * * *")
        job2 = MockJob(name="job2", cron_schedule="* * * * *")

        # Break the loop after 1 successful run to prevent hanging
        job1.run_once_mock.side_effect = [None, asyncio.CancelledError()]
        job2.run_once_mock.side_effect = [None, asyncio.CancelledError()]

        engine.add_job(job1)
        engine.add_job(job2)

        with patch("scheduler.jobs.base.croniter") as mock_croniter_class:
            mock_cron = MagicMock()
            mock_cron.get_next.return_value = datetime(2020, 1, 1, 0, 0, 0)
            mock_croniter_class.return_value = mock_cron

            with patch("scheduler.jobs.base.asyncio.sleep", new_callable=AsyncMock):
                try:
                    await engine.start()
                except asyncio.CancelledError:
                    pass

                job1.run_once_mock.assert_called()
                job2.run_once_mock.assert_called()

    async def test_scheduler_engine_start_with_no_jobs(self) -> None:
        """Test that starting the engine with no jobs logs a warning and returns early."""
        engine = SchedulerEngine()
        with patch("scheduler.core.logger.warning") as mock_warning:
            await engine.start()
            mock_warning.assert_called_once_with("No jobs to start.")


class MarketDataCollectorJobTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.config = MarketDataCollectorConfig(
            symbol="SPY",
            data_type=DataType.OPTION_CHAIN,
            cron_schedule="* * * * *",
            provider="yahoo",
        )

    async def test_market_data_collector_bar_success(self) -> None:
        """Test that MarketDataCollectorJob successfully fetches a bar and logs success."""
        config = MarketDataCollectorConfig(
            symbol="AAPL",
            data_type=DataType.BAR,
            cron_schedule="* * * * *",
            provider="yahoo",
        )
        job = MarketDataCollectorJob(config=config)

        mock_feed = MagicMock()
        mock_feed.get_current_bar = AsyncMock()

        with patch.object(job, "_provider_map", {"yahoo": MagicMock(return_value=mock_feed)}):
            await job.run_once()

        mock_feed.get_current_bar.assert_called_once_with("AAPL")

    async def test_market_data_collector_option_chain_success(self) -> None:
        """Test that MarketDataCollectorJob fetches all expirations concurrently and logs aggregated success."""
        job = MarketDataCollectorJob(config=self.config)

        mock_feed = MagicMock()
        mock_feed.get_option_expirations = AsyncMock(return_value=["2024-01-19", "2024-01-26"])

        mock_chain1 = MagicMock(spec=OptionChain)
        mock_chain1.contracts = ["C1", "C2"]
        mock_chain2 = MagicMock(spec=OptionChain)
        mock_chain2.contracts = ["C3"]

        mock_feed.get_current_option_chain = AsyncMock(side_effect=[mock_chain1, mock_chain2])

        with patch.object(job, "_provider_map", {"yahoo": MagicMock(return_value=mock_feed)}):
            with patch("scheduler.jobs.market_data_collector.logger.info") as mock_logger_info:
                await job.run_once()

        mock_feed.get_option_expirations.assert_called_once_with("SPY")
        self.assertEqual(mock_feed.get_current_option_chain.call_count, 2)

        mock_logger_info.assert_called_once()
        log_msg = mock_logger_info.call_args[0][0]
        self.assertIn("SUCCESS: SPY option_chain", log_msg)
        self.assertIn("2 expirations", log_msg)
        self.assertIn("3 contracts fetched", log_msg)

    async def test_market_data_collector_option_chain_no_expirations(self) -> None:
        """Test that MarketDataCollectorJob handles empty expirations gracefully with a warning."""
        job = MarketDataCollectorJob(config=self.config)

        mock_feed = MagicMock()
        mock_feed.get_option_expirations = AsyncMock(return_value=[])

        with patch.object(job, "_provider_map", {"yahoo": MagicMock(return_value=mock_feed)}):
            with patch("scheduler.jobs.market_data_collector.logger.warning") as mock_warning:
                await job.run_once()

        mock_warning.assert_called_once_with("No option expirations available for SPY")

    async def test_market_data_collector_unknown_provider(self) -> None:
        """Test that MarketDataCollectorJob logs an error when an unknown provider is specified."""
        config = MarketDataCollectorConfig(
            symbol="SPY",
            data_type=DataType.BAR,
            cron_schedule="* * * * *",
            provider="unknown",
        )
        job = MarketDataCollectorJob(config=config)

        with patch("scheduler.jobs.market_data_collector.logger.error") as mock_error:
            await job.run_once()

        mock_error.assert_called_once_with("Unknown provider: unknown")

    async def test_market_data_collector_handles_exceptions(self) -> None:
        """Test that MarketDataCollectorJob catches and logs exceptions during execution (Log and Skip)."""
        job = MarketDataCollectorJob(config=self.config)

        mock_feed = MagicMock()
        mock_feed.get_option_expirations = AsyncMock(side_effect=RuntimeError("Network error"))

        with patch.object(job, "_provider_map", {"yahoo": MagicMock(return_value=mock_feed)}):
            with patch("scheduler.jobs.market_data_collector.logger.error") as mock_error:
                await job.run_once()

        mock_error.assert_called_once()
        self.assertIn("FAILED: SPY option_chain", mock_error.call_args[0][0])
        self.assertIn("Network error", mock_error.call_args[0][0])


class MainEntryPointTests(unittest.TestCase):
    def test_load_config_valid(self) -> None:
        """Test that load_config correctly parses a valid YAML configuration file."""
        from scheduler.__main__ import load_config

        yaml_content = """
jobs:
  - type: market_data_collector
    config:
      symbol: SPY
      data_type: bar
      provider: yahoo
      cron_schedule: "* * * * *"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            self.assertEqual(len(config.jobs), 1)
            self.assertEqual(config.jobs[0].config.symbol, "SPY")
        finally:
            os.unlink(temp_path)

    def test_load_config_file_not_found(self) -> None:
        """Test that load_config raises FileNotFoundError when the configuration file does not exist."""
        from scheduler.__main__ import load_config

        with self.assertRaises(FileNotFoundError):
            load_config("non_existent_file.yaml")

    def test_instantiate_jobs_valid(self) -> None:
        """Test that instantiate_jobs correctly creates MarketDataCollectorJob instances from config."""
        from scheduler.__main__ import instantiate_jobs

        config_data = {
            "jobs": [
                {
                    "type": "market_data_collector",
                    "config": {
                        "symbol": "SPY",
                        "data_type": "bar",
                        "cron_schedule": "* * * * *",
                        "provider": "yahoo",
                    },
                }
            ]
        }
        config = SchedulerConfig.model_validate(config_data)
        jobs = instantiate_jobs(config)

        self.assertEqual(len(jobs), 1)
        self.assertIsInstance(jobs[0], MarketDataCollectorJob)
        self.assertEqual(jobs[0].name, "collect_yahoo_SPY_bar")

    def test_instantiate_jobs_empty(self) -> None:
        """Test that instantiate_jobs returns an empty list when no jobs are configured."""
        from scheduler.__main__ import instantiate_jobs

        config = SchedulerConfig(jobs=[])
        jobs = instantiate_jobs(config)
        self.assertEqual(len(jobs), 0)
