
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from quantedge.market_data.models import (
    CandleTimeframe,
    MarketCandle,
)


def test_create_valid_futures_candle():
    candle = MarketCandle(
        instrument_id="QE-FUT-001",
        timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
        timeframe=CandleTimeframe.ONE_MINUTE,
        open=Decimal("25100.00"),
        high=Decimal("25115.00"),
        low=Decimal("25095.00"),
        close=Decimal("25110.00"),
        volume=12500,
    )

    assert candle.instrument_id == "QE-FUT-001"
    assert candle.close == Decimal("25110.00")
    assert candle.volume == 12500


def test_create_index_candle_without_volume():
    candle = MarketCandle(
        instrument_id="QE-INDEX-001",
        timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
        open=Decimal("25100"),
        high=Decimal("25115"),
        low=Decimal("25095"),
        close=Decimal("25110"),
        volume=None,
    )

    assert candle.volume is None


def test_timestamp_normalized_to_utc():
    candle = MarketCandle(
        instrument_id="QE-INDEX-001",
        timestamp=datetime(
            2026, 11, 18, 9, 15,
            tzinfo=timezone(timedelta(hours=5, minutes=30)),
        ),
        open=Decimal("25100"),
        high=Decimal("25115"),
        low=Decimal("25095"),
        close=Decimal("25110"),
    )

    assert candle.timestamp == datetime(
        2026, 11, 18, 3, 45, tzinfo=timezone.utc
    )


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError, match="timezone-aware"):
        MarketCandle(
            instrument_id="QE-INDEX-001",
            timestamp=datetime(2026, 11, 18, 9, 15),
            open=Decimal("25100"),
            high=Decimal("25115"),
            low=Decimal("25095"),
            close=Decimal("25110"),
        )


def test_invalid_high_rejected():
    with pytest.raises(ValidationError, match="High must be"):
        MarketCandle(
            instrument_id="QE-FUT-001",
            timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
            open=Decimal("25100"),
            high=Decimal("25090"),
            low=Decimal("25080"),
            close=Decimal("25110"),
        )


def test_invalid_low_rejected():
    with pytest.raises(ValidationError, match="Low must be"):
        MarketCandle(
            instrument_id="QE-FUT-001",
            timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
            open=Decimal("25100"),
            high=Decimal("25120"),
            low=Decimal("25105"),
            close=Decimal("25110"),
        )


def test_negative_volume_rejected():
    with pytest.raises(ValidationError):
        MarketCandle(
            instrument_id="QE-FUT-001",
            timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
            open=Decimal("25100"),
            high=Decimal("25115"),
            low=Decimal("25095"),
            close=Decimal("25110"),
            volume=-100,
        )
