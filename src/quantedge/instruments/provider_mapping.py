
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InstrumentProviderMapping(BaseModel):

    model_config = ConfigDict(
        frozen=True,
        extra="forbid"
    )

    mapping_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)

    provider: str = Field(min_length=1)
    provider_instrument_id: str = Field(min_length=1)
    provider_symbol: str = Field(min_length=1)

    exchange: str = Field(min_length=1)
    segment: str = Field(min_length=1)

    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_mapping(self):

        if self.valid_to is not None:
            if self.valid_to < self.valid_from:
                raise ValueError(
                    "valid_to cannot be earlier than valid_from"
                )

        return self
