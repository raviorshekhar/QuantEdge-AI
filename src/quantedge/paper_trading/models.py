from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TradeSignal(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid"
    )

    signal_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)

    direction: SignalDirection

    suggested_entry: Decimal = Field(gt=0)
    suggested_stop_loss: Decimal = Field(gt=0)
    suggested_target: Decimal = Field(gt=0)

    generated_at: datetime
    expires_at: datetime

    status: SignalStatus = SignalStatus.PENDING
    decided_at: datetime | None = None
    decision_reason: str | None = None

    @field_validator("generated_at", "expires_at", "decided_at")
    @classmethod
    def normalize_timestamp(
        cls,
        value: datetime | None
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_signal(self):

        if self.expires_at <= self.generated_at:
            raise ValueError(
                "expires_at must be later than generated_at"
            )

        if self.direction == SignalDirection.LONG:
            if not (
                self.suggested_stop_loss
                < self.suggested_entry
                < self.suggested_target
            ):
                raise ValueError(
                    "LONG signal requires SL < Entry < Target"
                )

        if self.direction == SignalDirection.SHORT:
            if not (
                self.suggested_target
                < self.suggested_entry
                < self.suggested_stop_loss
            ):
                raise ValueError(
                    "SHORT signal requires Target < Entry < SL"
                )

        if self.status == SignalStatus.PENDING:
            if self.decided_at is not None:
                raise ValueError(
                    "Pending signal cannot have decided_at"
                )

        elif self.decided_at is None:
            raise ValueError(
                "Non-pending signal requires decided_at"
            )

        return self