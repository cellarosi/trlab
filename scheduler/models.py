"""
Configuration models for the scheduler application.

Design Rationale:
- Strict, flat configuration parsing using Pydantic to ensure 1:1 mapping between 
  a YAML job entry and a BaseJob instance.
- Eliminates unnecessary nesting to keep configuration intuitive.
- Uses discriminated unions (via `type` field) to allow the Scheduler to easily 
  instantiate the correct job class and to seamlessly accommodate new types of 
  scheduled jobs in the future without modifying the base config parser.
"""

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Represents the type of market data to collect, as defined in the perpetual 
    feed download plan (bar or option_chain, where option_chain fetches all 
    expirations and all strikes)."""
    BAR = "bar"
    OPTION_CHAIN = "option_chain"


class MarketDataCollectorConfig(BaseModel):
    """Specific configuration for the market data collection job.
    Maps directly to the 'config' block in the YAML under the market_data_collector 
    job type."""
    symbol: str
    data_type: DataType
    cron_schedule: str
    provider: str


class MarketDataCollectorJobConfig(BaseModel):
    """Container for a market data collector job, using a literal 'type' for 
    discriminated union resolution."""
    type: Literal["market_data_collector"]
    config: MarketDataCollectorConfig


JobConfig = Annotated[
    Union[MarketDataCollectorJobConfig],
    Field(discriminator="type")
]
"""
Union type using a discriminator. 
Why: Pydantic uses the 'type' field to automatically validate and parse the 
correct specific configuration model, making it trivial to add new job types 
later by simply adding them to this Union.
"""


class SchedulerConfig(BaseModel):
    """Top-level configuration model, holding a list of any configured jobs."""
    jobs: list[JobConfig]