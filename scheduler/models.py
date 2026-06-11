"""Configuration models for the scheduler application."""

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class DataType(str, Enum):
    BAR = "bar"
    OPTION_CHAIN = "option_chain"


class MarketDataCollectorConfig(BaseModel):
    symbol: str
    data_type: DataType
    cron_schedule: str
    provider: str


class MarketDataCollectorJobConfig(BaseModel):
    type: Literal["market_data_collector"]
    config: MarketDataCollectorConfig


JobConfig = Annotated[
    Union[MarketDataCollectorJobConfig],
    Field(discriminator="type")
]


class SchedulerConfig(BaseModel):
    jobs: list[JobConfig]