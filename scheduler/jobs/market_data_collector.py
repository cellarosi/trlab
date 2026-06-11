"""Market data collector job implementation."""

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
        job_name = f"collect_{config.provider}_{config.symbol}_{config.data_type.value}"
        super().__init__(name=job_name, cron_schedule=config.cron_schedule)
        self.config = config
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
                await feed.get_current_bar(self.config.symbol)
                logger.info(f"SUCCESS: {self.config.symbol} bar fetched")
                
            elif self.config.data_type == DataType.OPTION_CHAIN:
                expirations = await feed.get_option_expirations(self.config.symbol)
                if not expirations:
                    logger.warning(f"No option expirations available for {self.config.symbol}")
                    return
                
                tasks = [
                    feed.get_current_option_chain(self.config.symbol, expiration=exp) 
                    for exp in expirations
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                total_contracts = sum(
                    len(res.contracts) for res in results 
                    if isinstance(res, OptionChain)
                )
                logger.info(
                    f"SUCCESS: {self.config.symbol} option_chain - "
                    f"{len(expirations)} expirations, {total_contracts} contracts fetched"
                )
        except Exception as e:
            logger.error(f"FAILED: {self.config.symbol} {self.config.data_type.value} - {e}")