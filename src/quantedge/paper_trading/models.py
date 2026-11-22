
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field,
)


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalDecisionType(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TradeSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

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

    @field_validator("generated_at", "expires_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
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

        elif self.direction == SignalDirection.SHORT:
            if not (
                self.suggested_target
                < self.suggested_entry
                < self.suggested_stop_loss
            ):
                raise ValueError(
                    "SHORT signal requires Target < Entry < SL"
                )

        return self


class SignalDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(min_length=1)
    signal_id: str = Field(min_length=1)
    decision: SignalDecisionType
    decided_at: datetime
    reason: str | None = None

    @field_validator("decided_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")

        return value.astimezone(timezone.utc)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @model_validator(mode="after")
    def validate_decision(self):
        if (
            self.decision == SignalDecisionType.REJECT
            and self.reason is None
        ):
            raise ValueError(
                "A reason is required when rejecting a signal"
            )

        return self


class PaperTrade(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    trade_id: str = Field(min_length=1)
    signal_id: str = Field(min_length=1)

    instrument_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)

    direction: SignalDirection

    number_of_lots: int = Field(gt=0)
    lot_size: int = Field(gt=0)

    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    target: Decimal = Field(gt=0)

    opened_at: datetime

    @computed_field
    @property
    def quantity(self) -> int:
        return self.number_of_lots * self.lot_size

    @field_validator("opened_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")

        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_trade(self):
        if self.direction == SignalDirection.LONG:
            if not (
                self.stop_loss < self.entry_price < self.target
            ):
                raise ValueError(
                    "LONG trade requires SL < Entry < Target"
                )

        elif self.direction == SignalDirection.SHORT:
            if not (
                self.target < self.entry_price < self.stop_loss
            ):
                raise ValueError(
                    "SHORT trade requires Target < Entry < SL"
                )

        return self


class ExecutionType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class TradeExecution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: str = Field(min_length=1)
    trade_id: str = Field(min_length=1)

    execution_type: ExecutionType

    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0)

    charges: Decimal = Field(default=Decimal("0"), ge=0)

    executed_at: datetime

    @field_validator("executed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Execution timestamp must be timezone-aware")

        return value.astimezone(timezone.utc)
