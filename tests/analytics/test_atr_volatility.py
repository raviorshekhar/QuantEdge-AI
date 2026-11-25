
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from quantedge.analytics.indicators import (
    calculate_atr,
    calculate_historical_volatility,
)
from quantedge.market_data.models import CandleTimeframe, MarketCandle


def make_candle(
    index: int,
    high: str,
    low: str,
    close: str,
    instrument_id: str = "NSE-FUT-NIFTY-20261229",
) -> MarketCandle:
    return MarketCandle(
        instrument_id=instrument_id,
        timestamp=datetime(2026, 11, 2, tzinfo=timezone.utc)
        + timedelta(minutes=index),
        timeframe=CandleTimeframe.ONE_MINUTE,
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
        open_interest=None,
    )


def test_atr_initial_average():
    candles = [
        make_candle(0, "110", "100", "105"),
        make_candle(1, "115", "105", "110"),
        make_candle(2, "120", "110", "115"),
    ]

    result = calculate_atr(candles, period=3)

    assert result[0] is None
    assert result[1] is None
    assert result[2] == Decimal("10")


def test_atr_wilder_smoothing():
    candles = [
        make_candle(0, "110", "100", "105"),
        make_candle(1, "115", "105", "110"),
        make_candle(2, "120", "110", "115"),
        make_candle(3, "130", "115", "125"),
    ]

    result = calculate_atr(candles, period=3)

    assert result[2] == Decimal("10")
    assert result[3] == Decimal(35) / Decimal(3)


def test_atr_uses_previous_close():
    candles = [
        make_candle(0, "110", "100", "105"),
        make_candle(1, "130", "125", "128"),
    ]

    result = calculate_atr(candles, period=2)

    # TR values: 10 and 25
    assert result[1] == Decimal("17.5")


def test_atr_empty_input():
    assert calculate_atr([]) == []


def test_atr_invalid_period():
    with pytest.raises(ValueError):
        calculate_atr([], period=0)


def test_atr_preserves_input_order():
    first = make_candle(0, "110", "100", "105")
    second = make_candle(1, "115", "105", "110")
    third = make_candle(2, "120", "110", "115")

    result = calculate_atr([third, first, second], period=2)

    assert result[0] == Decimal("10")
    assert result[1] is None
    assert result[2] == Decimal("10")


def test_historical_volatility_constant_prices():
    candles = [
        make_candle(i, "110", "100", "105")
        for i in range(4)
    ]

    result = calculate_historical_volatility(
        candles,
        period=2,
        annualization_factor=252,
    )

    assert result[0] is None
    assert result[1] is None
    assert result[2] == Decimal("0")
    assert result[3] == Decimal("0")


def test_historical_volatility_invalid_period():
    with pytest.raises(ValueError):
        calculate_historical_volatility([], period=1)


def test_historical_volatility_invalid_annualization():
    with pytest.raises(ValueError):
        calculate_historical_volatility([], annualization_factor=0)


def test_historical_volatility_empty_input():
    assert calculate_historical_volatility([]) == []
