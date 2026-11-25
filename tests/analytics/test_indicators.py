
from collections import defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt
from zoneinfo import ZoneInfo

from quantedge.market_data.models import MarketCandle


IST = ZoneInfo("Asia/Kolkata")


def _ordered_candles(
    candles: list[MarketCandle],
) -> list[tuple[int, MarketCandle]]:
    return sorted(
        enumerate(candles),
        key=lambda item: (
            item[1].instrument_id,
            item[1].timestamp,
        ),
    )


def calculate_vwap(
    candles: list[MarketCandle],
) -> list[Decimal | None]:
    """Calculate cumulative session VWAP, resetting each trading day."""

    results: list[Decimal | None] = [None] * len(candles)

    session_state: dict[
        tuple[str, date],
        tuple[Decimal, int],
    ] = {}

    for original_index, candle in _ordered_candles(candles):
        session_date = candle.timestamp.astimezone(IST).date()
        session_key = (candle.instrument_id, session_date)

        if candle.volume is None:
            results[original_index] = None
            continue

        typical_price = (
            candle.high + candle.low + candle.close
        ) / Decimal("3")

        cumulative_pv, cumulative_volume = session_state.get(
            session_key,
            (Decimal("0"), 0),
        )

        cumulative_pv += typical_price * candle.volume
        cumulative_volume += candle.volume

        session_state[session_key] = (
            cumulative_pv,
            cumulative_volume,
        )

        if cumulative_volume == 0:
            results[original_index] = None
        else:
            results[original_index] = (
                cumulative_pv / Decimal(cumulative_volume)
            )

    return results


def calculate_atr(
    candles: list[MarketCandle],
    period: int = 14,
) -> list[Decimal | None]:
    """
    Calculate Average True Range using Wilder's smoothing.

    True Range:
        max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )

    The first ATR is the arithmetic mean of the first `period`
    True Range values. Subsequent values use Wilder's smoothing.

    ATR is calculated independently per instrument and does not
    reset at session boundaries.

    Results preserve original input order.
    """

    if period < 1:
        raise ValueError("period must be greater than zero")

    results: list[Decimal | None] = [None] * len(candles)

    grouped: dict[str, list[tuple[int, MarketCandle]]] = defaultdict(list)

    for indexed_candle in _ordered_candles(candles):
        _, candle = indexed_candle
        grouped[candle.instrument_id].append(indexed_candle)

    decimal_period = Decimal(period)

    for instrument_candles in grouped.values():
        previous_close: Decimal | None = None
        true_ranges: list[Decimal] = []
        current_atr: Decimal | None = None

        for original_index, candle in instrument_candles:
            if previous_close is None:
                true_range = candle.high - candle.low
            else:
                true_range = max(
                    candle.high - candle.low,
                    abs(candle.high - previous_close),
                    abs(candle.low - previous_close),
                )

            true_ranges.append(true_range)
            previous_close = candle.close

            if len(true_ranges) < period:
                continue

            if current_atr is None:
                current_atr = (
                    sum(true_ranges[:period], Decimal("0"))
                    / decimal_period
                )
            else:
                current_atr = (
                    current_atr * Decimal(period - 1) + true_range
                ) / decimal_period

            results[original_index] = current_atr

    return results


def calculate_historical_volatility(
    candles: list[MarketCandle],
    period: int = 20,
    annualization_factor: int = 252,
) -> list[Decimal | None]:
    """
    Calculate rolling annualized historical volatility.

    Uses the standard deviation of logarithmic close-to-close returns.

    Formula:
        HV = standard_deviation(log_returns) * sqrt(annualization_factor)

    `period` is the number of returns in each rolling window.
    The default annualization factor of 252 assumes daily candles.

    For intraday candles, supply an appropriate annualization factor.
    Results preserve original input order.

    The first candle per instrument has no return and therefore
    cannot produce a volatility value.
    """

    if period < 2:
        raise ValueError("period must be at least 2")

    if annualization_factor < 1:
        raise ValueError("annualization_factor must be greater than zero")

    results: list[Decimal | None] = [None] * len(candles)

    grouped: dict[str, list[tuple[int, MarketCandle]]] = defaultdict(list)

    for indexed_candle in _ordered_candles(candles):
        _, candle = indexed_candle
        grouped[candle.instrument_id].append(indexed_candle)

    annualization = Decimal(annualization_factor).sqrt()

    for instrument_candles in grouped.values():
        returns: list[Decimal] = []
        previous_close: Decimal | None = None

        for original_index, candle in instrument_candles:
            if previous_close is None:
                previous_close = candle.close
                continue

            log_return = (
                candle.close / previous_close
            ).ln()

            returns.append(log_return)
            previous_close = candle.close

            if len(returns) < period:
                continue

            window = returns[-period:]
            mean = sum(window, Decimal("0")) / Decimal(period)

            squared_deviations = [
                (value - mean) ** 2 for value in window
            ]

            variance = (
                sum(squared_deviations, Decimal("0"))
                / Decimal(period - 1)
            )

            volatility = variance.sqrt() * annualization

            results[original_index] = volatility

    return results
