from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from quantedge.paper_trading.lifecycle import (
    SignalLifecycle,
    SignalNotFoundError,
)
from quantedge.paper_trading.models import (
    PaperTrade,
    SignalDecisionType,
)


class SignalNotAcceptedError(Exception):
    pass


class DuplicatePaperTradeError(Exception):
    pass


class InvalidTradeOpeningTimeError(Exception):
    pass


class PaperTradingService:

    def __init__(self, signal_lifecycle: SignalLifecycle):
        self._signal_lifecycle = signal_lifecycle
        self._trades: dict[str, PaperTrade] = {}
        self._signal_trade_mapping: dict[str, str] = {}

    def create_trade(
        self,
        signal_id: str,
        number_of_lots: int,
        lot_size: int,
        entry_price: Decimal,
        opened_at: datetime,
    ) -> PaperTrade:

        signal = self._signal_lifecycle.get_signal(signal_id)

        decision = self._signal_lifecycle.get_decision(signal_id)

        if (
            decision is None
            or decision.decision != SignalDecisionType.ACCEPT
        ):
            raise SignalNotAcceptedError(
                "Paper trade requires an accepted signal"
            )

        if signal_id in self._signal_trade_mapping:
            raise DuplicatePaperTradeError(
                "Paper trade already exists for this signal"
            )

        if opened_at.tzinfo is None or opened_at.utcoffset() is None:
            raise ValueError(
                "Trade opening timestamp must be timezone-aware"
            )

        opened_at = opened_at.astimezone(timezone.utc)

        if opened_at < decision.decided_at:
            raise InvalidTradeOpeningTimeError(
                "Trade cannot open before signal acceptance"
            )

        trade = PaperTrade(
            trade_id=str(uuid4()),
            signal_id=signal.signal_id,
            instrument_id=signal.instrument_id,
            strategy_id=signal.strategy_id,
            strategy_version=signal.strategy_version,
            direction=signal.direction,
            number_of_lots=number_of_lots,
            lot_size=lot_size,
            entry_price=entry_price,
            stop_loss=signal.suggested_stop_loss,
            target=signal.suggested_target,
            opened_at=opened_at,
        )

        self._trades[trade.trade_id] = trade
        self._signal_trade_mapping[signal_id] = trade.trade_id

        return trade

    def get_trade(self, trade_id: str) -> PaperTrade | None:
        return self._trades.get(trade_id)

    def get_trade_by_signal(self, signal_id: str) -> PaperTrade | None:
        trade_id = self._signal_trade_mapping.get(signal_id)

        if trade_id is None:
            return None

        return self._trades.get(trade_id)