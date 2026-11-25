
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InstrumentType(str, Enum):
    INDEX = "INDEX"
    FUTURE = "FUTURE"


class InstrumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    INACTIVE = "INACTIVE"


class Instrument(BaseModel):

    model_config = ConfigDict(
        frozen=True,
        extra="forbid"
    )

    instrument_id: str = Field(min_length=1)
    exchange: str
    instrument_type: InstrumentType
    symbol: str
    name: str

    underlying_id: str | None = None
    expiry_date: date | None = None

    # Exchange-provided trading specifications.
    # Keep optional because metadata may not be available at registration time.
    lot_size: int | None = Field(default=None, gt=0)
    tick_size: Decimal | None = Field(default=None, gt=0)

    currency: str = "INR"
    status: InstrumentStatus = InstrumentStatus.ACTIVE

    @model_validator(mode="after")
    def validate_instrument(self):

        if self.instrument_type == InstrumentType.INDEX:

            if self.underlying_id is not None:
                raise ValueError(
                    "An index cannot have an underlying_id"
                )

            if self.expiry_date is not None:
                raise ValueError(
                    "An index cannot have an expiry_date"
                )

            if self.lot_size is not None:
                raise ValueError(
                    "An index cannot have a lot_size"
                )

        if self.instrument_type == InstrumentType.FUTURE:

            if not self.underlying_id:
                raise ValueError(
                    "A futures contract requires an underlying_id"
                )

            if not self.expiry_date:
                raise ValueError(
                    "A futures contract requires an expiry_date"
                )

            if self.underlying_id == self.instrument_id:
                raise ValueError(
                    "An instrument cannot reference itself as underlying"
                )

        return self
