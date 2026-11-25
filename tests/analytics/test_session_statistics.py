
from datetime import datetime, timezone
from decimal import Decimal

from quantedge.analytics.session_statistics import (
    calculate_session_statistics,
)
from quantedge.market_data.models import CandleTimeframe, MarketCandle


def make_candle(
    timestamp: datetime,
    high: str,
    low: str,
    close: str,
    volume: int | None,
) -> MarketCandle:
    return MarketCandle(
        instrument_id="NSE-FUT-NIFTY-20261229",
        timestamp=timestamp,
        timeframe=CandleTimeframe.ONE_MINUTE,
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
        open_interest=None,
    )


def test_session_statistics():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "110", "100", "105", 100,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 46, tzinfo=timezone.utc),
            "120", "105", "115", 200,
        ),
    ]

    result = calculate_session_statistics(candles)

    assert len(result) == 1

    session = result[0]

    assert session.open == Decimal("105")
    assert session.high == Decimal("120")
    assert session.low == Decimal("100")
    assert session.close == Decimal("115")
    assert session.volume == 300
    assert session.candle_count == 2
    assert session.price_range == Decimal("20")
    assert session.change == Decimal("10")
    assert session.change_percent == (
        Decimal("10") / Decimal("105") * Decimal("100")
    )


def test_session_statistics_missing_volume():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "110", "100", "105", 100,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 46, tzinfo=timezone.utc),
            "120", "105", "115", None,
        ),
    ]

    result = calculate_session_statistics(candles)

    assert result[0].volume is None


def test_session_statistics_empty_input():
    assert calculate_session_statistics([]) == []
