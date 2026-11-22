
from datetime import datetime, timezone
from uuid import uuid4

from quantedge.paper_trading.models import (
    SignalDecision,
    SignalDecisionType,
    SignalStatus,
    TradeSignal,
)


class SignalNotFoundError(Exception):
    """Raised when a signal does not exist."""


class SignalExpiredError(Exception):
    """Raised when an expired signal is being accepted or rejected."""


class DuplicateSignalDecisionError(Exception):
    """Raised when a signal already has a decision."""


class InvalidSignalDecisionTimeError(ValueError):
    """Raised when a decision timestamp is invalid."""


class InvalidSignalDecisionError(ValueError):
    """Raised when a signal decision violates business rules."""


class SignalLifecycle:

    def __init__(self):
        self._signals: dict[str, TradeSignal] = {}
        self._decisions: dict[str, SignalDecision] = {}

    def register_signal(self, signal: TradeSignal) -> None:
        if signal.signal_id in self._signals:
            raise ValueError("Signal already exists")

        self._signals[signal.signal_id] = signal

    def get_signal(self, signal_id: str) -> TradeSignal:
        signal = self._signals.get(signal_id)

        if signal is None:
            raise SignalNotFoundError("Signal does not exist")

        return signal

    def decide(
        self,
        signal_id: str,
        decision: SignalDecisionType,
        decided_at: datetime,
        reason: str | None = None,
    ) -> SignalDecision:

        signal = self.get_signal(signal_id)

        if signal_id in self._decisions:
            raise DuplicateSignalDecisionError(
                "Signal already has a decision"
            )

        if (
            decision == SignalDecisionType.REJECT
            and (reason is None or not reason.strip())
        ):
            raise InvalidSignalDecisionError(
                "A reason is required when rejecting a signal"
            )

        if decided_at.tzinfo is None or decided_at.utcoffset() is None:
            raise InvalidSignalDecisionTimeError(
                "Decision timestamp must be timezone-aware"
            )

        decided_at = decided_at.astimezone(timezone.utc)

        if decided_at < signal.generated_at:
            raise InvalidSignalDecisionTimeError(
                "Decision cannot occur before signal generation"
            )

        if decided_at >= signal.expires_at:
            raise SignalExpiredError(
                "Signal has expired and can no longer be accepted or rejected"
            )

        signal_decision = SignalDecision(
            decision_id=str(uuid4()),
            signal_id=signal_id,
            decision=decision,
            decided_at=decided_at,
            reason=reason,
        )

        self._decisions[signal_id] = signal_decision

        return signal_decision

    def get_decision(self, signal_id: str) -> SignalDecision | None:
        self.get_signal(signal_id)
        return self._decisions.get(signal_id)

    def get_status(
        self,
        signal_id: str,
        as_of: datetime | None = None,
    ) -> SignalStatus:

        signal = self.get_signal(signal_id)

        decision = self._decisions.get(signal_id)

        if decision is not None:
            if decision.decision == SignalDecisionType.ACCEPT:
                return SignalStatus.ACCEPTED

            return SignalStatus.REJECTED

        if as_of is None:
            as_of = datetime.now(timezone.utc)

        elif as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("Status timestamp must be timezone-aware")

        as_of = as_of.astimezone(timezone.utc)

        if as_of >= signal.expires_at:
            return SignalStatus.EXPIRED

        return SignalStatus.PENDING
