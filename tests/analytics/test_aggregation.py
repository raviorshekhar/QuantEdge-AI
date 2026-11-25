
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from quantedge.analytics.aggregation import (
    DailyOHLCV,
    aggregate_daily_ohlcv,
)
from quantedge.market_data.models import CandleTimeframe, MarketCandle


def make_candle(
    timestamp: datetime,
    open_price: str,
    high: str,
    low: str,
    close: str,
    volume: int | None,
    instrument_id: str = "NSE-FUT-NIFTY-20261229",
) -> MarketCandle:
    return MarketCandle(
        instrument_id=instrument_id,
        timestamp=timestamp,
        timeframe=CandleTimeframe.ONE_MINUTE,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
        open_interest=None,
    )


def test_daily_ohlcv_aggregation():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 46, tzinfo=timezone.utc),
            "104", "110", "102", "108", 200,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 47, tzinfo=timezone.utc),
            "108", "109", "103", "106", 150,
        ),
    ]

    result = aggregate_daily_ohlcv(candles)

    assert len(result) == 1

    daily = result[0]

    assert daily.trading_date == date(2026, 11, 2)
    assert daily.open == Decimal("100")
    assert daily.high == Decimal("110")
    assert daily.low == Decimal("99")
    assert daily.close == Decimal("106")
    assert daily.volume == 450
    assert daily.candle_count == 3


def test_aggregation_sorts_unsorted_input():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 47, tzinfo=timezone.utc),
            "108", "109", "103", "106", 150,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
    ]

    daily = aggregate_daily_ohlcv(candles)[0]

    assert daily.open == Decimal("100")
    assert daily.close == Decimal("106")
    assert daily.volume == 250


def test_aggregation_separates_trading_dates():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
        make_candle(
            datetime(2026, 11, 3, 3, 45, tzinfo=timezone.utc),
            "110", "115", "109", "114", 200,
        ),
    ]

    result = aggregate_daily_ohlcv(candles)

    assert len(result) == 2
    assert result[0].trading_date == date(2026, 11, 2)
    assert result[1].trading_date == date(2026, 11, 3)


def test_aggregation_separates_instruments():
    timestamp = datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc)

    candles = [
        make_candle(timestamp, "100", "105", "99", "104", 100),
        make_candle(
            timestamp, "200", "205", "199", "204", 200,
            instrument_id="NSE-FUT-BANKNIFTY-20261229",
        ),
    ]

    result = aggregate_daily_ohlcv(candles)

    assert len(result) == 2
    assert result[0].instrument_id == "NSE-FUT-BANKNIFTY-20261229"
    assert result[1].instrument_id == "NSE-FUT-NIFTY-20261229"


def test_missing_volume_produces_none_daily_volume():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 46, tzinfo=timezone.utc),
            "104", "110", "102", "108", None,
        ),
    ]

    daily = aggregate_daily_ohlcv(candles)[0]

    assert daily.volume is None
    assert daily.candle_count == 2


def test_zero_volume_is_preserved():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
        make_candle(
            datetime(2026, 11, 2, 3, 46, tzinfo=timezone.utc),
            "104", "104", "104", "104", 0,
        ),
    ]

    daily = aggregate_daily_ohlcv(candles)[0]

    assert daily.volume == 100
    assert daily.candle_count == 2


def test_empty_input_returns_empty_list():
    assert aggregate_daily_ohlcv([]) == []


def test_output_records_are_immutable():
    candles = [
        make_candle(
            datetime(2026, 11, 2, 3, 45, tzinfo=timezone.utc),
            "100", "105", "99", "104", 100,
        ),
    ]

    daily = aggregate_daily_ohlcv(candles)[0]

    with pytest.raises(AttributeError):
        daily.volume = 500
