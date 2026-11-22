
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from quantedge.paper_trading.models import (
    ExecutionType,
    TradeExecution,
)


@pytest.fixture
def execution():
    return TradeExecution(
        execution_id="EXEC-001",
        trade_id="TRADE-001",
        execution_type=ExecutionType.ENTRY,
        quantity=65,
        price=Decimal("25105"),
        charges=Decimal("10"),
        executed_at=datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
    )


def test_create_entry_execution(execution):
    assert execution.execution_type == ExecutionType.ENTRY
    assert execution.price == Decimal("25105")
    assert execution.quantity == 65


def test_create_exit_execution():
    execution = TradeExecution(
        execution_id="EXEC-002",
        trade_id="TRADE-001",
        execution_type=ExecutionType.EXIT,
        quantity=65,
        price=Decimal("25200"),
        executed_at=datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc),
    )

    assert execution.execution_type == ExecutionType.EXIT


def test_default_charges_are_zero(execution):
    assert execution.charges == Decimal("10")


def test_execution_rejects_zero_quantity():
    with pytest.raises(ValidationError):
        TradeExecution(
            execution_id="EXEC-003",
            trade_id="TRADE-001",
            execution_type=ExecutionType.ENTRY,
            quantity=0,
            price=Decimal("25105"),
            executed_at=datetime.now(timezone.utc),
        )


def test_execution_rejects_negative_price():
    with pytest.raises(ValidationError):
        TradeExecution(
            execution_id="EXEC-004",
            trade_id="TRADE-001",
            execution_type=ExecutionType.ENTRY,
            quantity=65,
            price=Decimal("-100"),
            executed_at=datetime.now(timezone.utc),
        )


def test_execution_rejects_negative_charges():
    with pytest.raises(ValidationError):
        TradeExecution(
            execution_id="EXEC-005",
            trade_id="TRADE-001",
            execution_type=ExecutionType.ENTRY,
            quantity=65,
            price=Decimal("25105"),
            charges=Decimal("-1"),
            executed_at=datetime.now(timezone.utc),
        )


def test_execution_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        TradeExecution(
            execution_id="EXEC-006",
            trade_id="TRADE-001",
            execution_type=ExecutionType.ENTRY,
            quantity=65,
            price=Decimal("25105"),
            executed_at=datetime(2026, 11, 20, 10, 0),
        )


def test_execution_timestamp_normalized_to_utc():
    execution = TradeExecution(
        execution_id="EXEC-007",
        trade_id="TRADE-001",
        execution_type=ExecutionType.ENTRY,
        quantity=65,
        price=Decimal("25105"),
        executed_at=datetime.fromisoformat("2026-11-20T15:30:00+05:30"),
    )

    assert execution.executed_at.hour == 10
    assert execution.executed_at.minute == 0
    assert execution.executed_at.utcoffset().total_seconds() == 0


def test_execution_is_immutable(execution):
    with pytest.raises(ValidationError):
        execution.price = Decimal("25200")
