from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from quantedge.paper_trading.models import (
    TradeSignal,
    SignalDirection,
    SignalStatus,
)


@pytest.fixture
def valid_long_signal():
    now = datetime.now(timezone.utc)

    return {
        "signal_id": "SIG-001",
        "instrument_id": "NIFTY-FUT-001",
        "strategy_id": "ORB-001",
        "strategy_version": "1.0",
        "direction": SignalDirection.LONG,
        "suggested_entry": Decimal("25100"),
        "suggested_stop_loss": Decimal("25050"),
        "suggested_target": Decimal("25200"),
        "generated_at": now,
        "expires_at": now + timedelta(minutes=15),
    }


def test_create_valid_long_signal(valid_long_signal):
    signal = TradeSignal(**valid_long_signal)

    assert signal.direction == SignalDirection.LONG
    assert signal.status == SignalStatus.PENDING


def test_create_valid_short_signal(valid_long_signal):
    valid_long_signal.update({
        "direction": SignalDirection.SHORT,
        "suggested_entry": Decimal("25100"),
        "suggested_stop_loss": Decimal("25150"),
        "suggested_target": Decimal("25000"),
    })

    signal = TradeSignal(**valid_long_signal)

    assert signal.direction == SignalDirection.SHORT


def test_invalid_long_signal_prices(valid_long_signal):
    valid_long_signal["suggested_stop_loss"] = Decimal("25150")

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)


def test_invalid_short_signal_prices(valid_long_signal):
    valid_long_signal.update({
        "direction": SignalDirection.SHORT,
        "suggested_stop_loss": Decimal("25050"),
        "suggested_target": Decimal("25200"),
    })

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)


def test_expiry_must_be_after_generation(valid_long_signal):
    valid_long_signal["expires_at"] = (
        valid_long_signal["generated_at"] - timedelta(minutes=1)
    )

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)


def test_naive_timestamp_not_allowed(valid_long_signal):
    valid_long_signal["generated_at"] = datetime(2026, 11, 20)

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)


def test_negative_entry_price_not_allowed(valid_long_signal):
    valid_long_signal["suggested_entry"] = Decimal("-100")

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)


def test_signal_is_immutable(valid_long_signal):
    signal = TradeSignal(**valid_long_signal)

    with pytest.raises(ValidationError):
        signal.status = SignalStatus.ACCEPTED


def test_unknown_field_not_allowed(valid_long_signal):
    valid_long_signal["random_field"] = "test"

    with pytest.raises(ValidationError):
        TradeSignal(**valid_long_signal)