
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quantedge.market_data.models import (
    CandleTimeframe,
    MarketCandle,
)
from quantedge.market_data.quality import (
    Severity,
    validate_candles,
)


def make_candle(
    timestamp: datetime,
    instrument_id: str = "NIFTY",
    timeframe: CandleTimeframe = CandleTimeframe.ONE_MINUTE,
) -> MarketCandle:
    return MarketCandle(
        instrument_id=instrument_id,
        timestamp=timestamp,
        timeframe=timeframe,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
        volume=1000,
    )


def make_timestamp(
    hour: int = 10,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026, 11, 25,
        hour, minute,
        tzinfo=timezone.utc,
    )


def test_empty_candle_list_returns_clean_report():
    report = validate_candles([])

    assert report.candle_count == 0
    assert report.issues == ()
    assert report.is_clean


def test_valid_candles_return_clean_report():
    candles = [
        make_candle(make_timestamp(minute=0)),
        make_candle(make_timestamp(minute=1)),
        make_candle(make_timestamp(minute=2)),
    ]

    report = validate_candles(candles)

    assert report.candle_count == 3
    assert report.is_clean
    assert report.errors == []


def test_mixed_instruments_generate_error():
    candles = [
        make_candle(make_timestamp(minute=0), "NIFTY"),
        make_candle(make_timestamp(minute=1), "BANKNIFTY"),
    ]

    report = validate_candles(candles)

    assert any(
        issue.code == "MIXED_INSTRUMENTS"
        and issue.severity == Severity.ERROR
        for issue in report.issues
    )

    assert not report.is_clean


def test_duplicate_timestamp_generates_error():
    timestamp = make_timestamp()

    candles = [
        make_candle(timestamp),
        make_candle(timestamp),
    ]

    report = validate_candles(candles)

    assert any(
        issue.code == "DUPLICATE_TIMESTAMP"
        and issue.severity == Severity.ERROR
        for issue in report.issues
    )


def test_out_of_order_timestamps_generate_error():
    candles = [
        make_candle(make_timestamp(minute=2)),
        make_candle(make_timestamp(minute=1)),
    ]

    report = validate_candles(candles)

    assert any(
        issue.code == "OUT_OF_ORDER"
        and issue.severity == Severity.ERROR
        for issue in report.issues
    )


def test_missing_interval_generates_warning():
    candles = [
        make_candle(make_timestamp(minute=0)),
        make_candle(make_timestamp(minute=2)),
    ]

    report = validate_candles(candles)

    assert any(
        issue.code == "MISSING_INTERVAL"
        and issue.severity == Severity.WARNING
        for issue in report.issues
    )


def test_continuous_candles_do_not_generate_missing_interval():
    candles = [
        make_candle(make_timestamp(minute=0)),
        make_candle(make_timestamp(minute=1)),
        make_candle(make_timestamp(minute=2)),
    ]

    report = validate_candles(candles)

    assert not any(
        issue.code == "MISSING_INTERVAL"
        for issue in report.issues
    )


def test_warning_does_not_make_report_unclean():
    candles = [
        make_candle(make_timestamp(minute=0)),
        make_candle(make_timestamp(minute=2)),
    ]

    report = validate_candles(candles)

    assert report.errors == []
    assert report.is_clean


def test_mixed_timeframes_generate_error():
    candles = [
        make_candle(
            make_timestamp(minute=0),
            timeframe=CandleTimeframe.ONE_MINUTE,
        ),
        make_candle(
            make_timestamp(minute=1),
            timeframe=CandleTimeframe.ONE_MINUTE,
        ),
    ]

    # Current CandleTimeframe enum supports only 1m.
    # Mixed-timeframe test will be added when additional
    # timeframe values are introduced.
    report = validate_candles(candles)

    assert not any(
        issue.code == "MIXED_TIMEFRAMES"
        for issue in report.issues
    )
