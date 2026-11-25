
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class CandleTimeframe(str, Enum):
    ONE_MINUTE = "1m"


class MarketCandle(BaseModel):

    model_config = ConfigDict(
        frozen=True,
        extra="forbid"
    )

    instrument_id: str = Field(min_length=1)

    timestamp: datetime

    timeframe: CandleTimeframe = CandleTimeframe.ONE_MINUTE

    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)

    volume: int | None = Field(default=None, ge=0)
    open_interest: int | None = Field(default=None, ge=0)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Timestamp must be timezone-aware"
            )

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_ohlc(self):

        if self.high < max(self.open, self.close, self.low):
            raise ValueError(
                "High must be greater than or equal to Open, Close and Low"
            )

        if self.low > min(self.open, self.close, self.high):
            raise ValueError(
                "Low must be less than or equal to Open, Close and High"
            )

        return self
