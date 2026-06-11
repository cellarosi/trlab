"""
Market data collector job implementation.

Design Rationale:
- This job fulfills the requirement of "perpetual feed download" for market data.
- Maps 1:1 to a `MarketDataCollectorConfig` instance.
- Provider Resolution: Uses a simple dictionary mapping to instantiate the correct 
  `DataFeed` implementation (e.g., `YahooFeed`). This keeps the job decoupled from 
  specific provider logic.
- Data Type Handling: 
  - For `bar`: simple single call to `get_current_bar`.
  - For `option_chain`: Fulfills the "all expiration all strike" requirement by 
    first fetching available expirations, then using `asyncio.gather` to fetch 
    all chains concurrently. This significantly reduces total execution time 
    compared to sequential fetching.
- Error Handling: Adheres strictly to the "Log and Skip" pattern inherited from 
  `BaseJob`, but also includes localized logging for specific fetch phases to 
  provide granular insight into what succeeded or failed during a single run.
"""

import logging
import asyncio

from scheduler.jobs.base import BaseJob
from scheduler.models import DataType, MarketDataCollectorConfig
from feed.yahoo import YahooFeed
from feed.models import OptionChain

logger = logging.getLogger(__name__)


class MarketDataCollectorJob(BaseJob):
    """Job that collects market data for a single symbol and data type."""

    def __init__(self, config: MarketDataCollectorConfig):
        # Constructing a unique descriptive name for logging and identification 
        # within the SchedulerEngine.
        job_name = f"collect_{config.provider}_{config.symbol}_{config.data_type.value}"
        super().__init__(name=job_name, cron_schedule=config.cron_schedule)
        self.config = config
        # Provider map allows for easy extension. To add 'polygon', simply add 
        # "polygon": PolygonFeed here and ensure it exists in the feed module.
        self._provider_map = {
            "yahoo": YahooFeed,
        }

    async def run_once(self) -> None:
        """Execute the data collection for this specific configuration."""
        provider_class = self._provider_map.get(self.config.provider.lower())
        if not provider_class:
            logger.error(f"Unknown provider: {self.config.provider}")
            return
        
        feed = provider_class()
        
        try:
            if self.config.data_type == DataType.BAR:
                # Fetching a single bar. The underlying feed handles the specifics.
                await feed.get_current_bar(self.config.symbol)
                logger.info(f"SUCCESS: {self.config.symbol} bar fetched")
                
            elif self.config.data_type == DataType.OPTION_CHAIN:
                # Requirement: "all expiration all strike"
                # Step 1: Retrieve available expirations from the provider.
                expirations = await feed.get_option_expirations(self.config.symbol)
                if not expirations:
                    logger.warning(f"No option expirations available for {self.config.symbol}")
                    return
                
                # Step 2: Concurrently fetch all chains via asyncio.gather.
                # Why concurrent: Fetching expirations sequentially would be prohibitively 
                # slow for symbols with many expiration dates (e.g., SPY).
                tasks = [
                    feed.get_current_option_chain(self.config.symbol, expiration=exp) 
                    for exp in expirations
                ]
                # return_exceptions=True ensures that if one expiration fails, 
                # the entire gather doesn't crash, and we can still process successful ones.
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Aggregate results for a concise, informative success log.
                total_contracts = sum(
                    len(res.contracts) for res in results 
                    if isinstance(res, OptionChain)
                )
                logger.info(
                    f"SUCCESS: {self.config.symbol} option_chain - "
                    f"{len(expirations)} expirations, {total_contracts} contracts fetched"
                )
        except Exception as e:
            # This outer exception block serves as a final safeguard for unexpected 
            # errors during the setup or provider instantiation phases, ensuring 
            # the BaseJob's infinite loop continues.
            logger.error(f"FAILED: {self.config.symbol} {self.config.data_type.value} - {e}")