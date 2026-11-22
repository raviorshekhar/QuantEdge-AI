
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quantedge.paper_trading.lifecycle import (
    DuplicateSignalDecisionError,
    InvalidSignalDecisionError,
    InvalidSignalDecisionTimeError,
    SignalExpiredError,
    SignalLifecycle,
    SignalNotFoundError,
)
from quantedge.paper_trading.models import (
    SignalDecisionType,
    SignalDirection,
    SignalStatus,
    TradeSignal,
)


@pytest.fixture
def signal_lifecycle():
    return SignalLifecycle()


@pytest.fixture
def valid_signal():
    return TradeSignal(
        signal_id="SIG-001",
        instrument_id="QE-INDEX-001",
        strategy_id="STRATEGY-001",
        strategy_version="1.0",
        direction=SignalDirection.LONG,
        suggested_entry=Decimal("25000"),
        suggested_stop_loss=Decimal("24900"),
        suggested_target=Decimal("25200"),
        generated_at=datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc),
    )


def test_register_and_get_signal(signal_lifecycle, valid_signal):
    signal_lifecycle.register_signal(valid_signal)

    result = signal_lifecycle.get_signal(valid_signal.signal_id)

    assert result == valid_signal


def test_duplicate_signal_registration_rejected(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    with pytest.raises(ValueError, match="Signal already exists"):
        signal_lifecycle.register_signal(valid_signal)


def test_get_nonexistent_signal_raises_error(signal_lifecycle):
    with pytest.raises(SignalNotFoundError):
        signal_lifecycle.get_signal("UNKNOWN-SIGNAL")


def test_accept_signal_without_reason(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    decision = signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.ACCEPT,
        decided_at=valid_signal.generated_at,
    )

    assert decision.decision == SignalDecisionType.ACCEPT
    assert decision.reason is None


def test_reject_signal_with_reason(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    decision = signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.REJECT,
        decided_at=valid_signal.generated_at,
        reason="Market conditions changed",
    )

    assert decision.decision == SignalDecisionType.REJECT
    assert decision.reason == "Market conditions changed"


def test_reject_signal_without_reason_fails(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    with pytest.raises(
        InvalidSignalDecisionError,
        match="reason is required",
    ):
        signal_lifecycle.decide(
            signal_id=valid_signal.signal_id,
            decision=SignalDecisionType.REJECT,
            decided_at=valid_signal.generated_at,
        )

    assert signal_lifecycle.get_decision(valid_signal.signal_id) is None


def test_duplicate_signal_decision_rejected(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.ACCEPT,
        decided_at=valid_signal.generated_at,
    )

    with pytest.raises(DuplicateSignalDecisionError):
        signal_lifecycle.decide(
            signal_id=valid_signal.signal_id,
            decision=SignalDecisionType.REJECT,
            decided_at=valid_signal.generated_at,
            reason="Changed my mind",
        )


def test_decision_before_signal_generation_rejected(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    earlier_time = datetime(
        2026, 11, 20, 9, 59, tzinfo=timezone.utc
    )

    with pytest.raises(
        InvalidSignalDecisionTimeError,
        match="before signal generation",
    ):
        signal_lifecycle.decide(
            signal_id=valid_signal.signal_id,
            decision=SignalDecisionType.ACCEPT,
            decided_at=earlier_time,
        )


def test_decision_at_expiry_rejected(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    with pytest.raises(SignalExpiredError):
        signal_lifecycle.decide(
            signal_id=valid_signal.signal_id,
            decision=SignalDecisionType.ACCEPT,
            decided_at=valid_signal.expires_at,
        )


def test_signal_status_pending_before_expiry(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    status = signal_lifecycle.get_status(
        valid_signal.signal_id,
        as_of=datetime(
            2026, 11, 20, 10, 30, tzinfo=timezone.utc
        ),
    )

    assert status == SignalStatus.PENDING


def test_signal_status_expired_at_expiry(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    status = signal_lifecycle.get_status(
        valid_signal.signal_id,
        as_of=valid_signal.expires_at,
    )

    assert status == SignalStatus.EXPIRED


def test_signal_status_accepted_after_acceptance(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.ACCEPT,
        decided_at=valid_signal.generated_at,
    )

    status = signal_lifecycle.get_status(
        valid_signal.signal_id,
        as_of=valid_signal.expires_at,
    )

    assert status == SignalStatus.ACCEPTED


def test_signal_status_rejected_after_rejection(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.REJECT,
        decided_at=valid_signal.generated_at,
        reason="Risk is too high",
    )

    status = signal_lifecycle.get_status(
        valid_signal.signal_id,
    )

    assert status == SignalStatus.REJECTED


def test_original_signal_remains_unchanged_after_decision(
    signal_lifecycle, valid_signal
):
    signal_lifecycle.register_signal(valid_signal)

    original_signal = signal_lifecycle.get_signal(
        valid_signal.signal_id
    )

    signal_lifecycle.decide(
        signal_id=valid_signal.signal_id,
        decision=SignalDecisionType.ACCEPT,
        decided_at=valid_signal.generated_at,
    )

    retrieved_signal = signal_lifecycle.get_signal(
        valid_signal.signal_id
    )

    assert retrieved_signal == original_signal
    assert retrieved_signal.signal_id == valid_signal.signal_id
