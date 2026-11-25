
from collections import defaultdict
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantedge.market_data.models import MarketCandle


IST = ZoneInfo("Asia/Kolkata")


def _ordered_candles(candles: list[MarketCandle]):
    return sorted(
        enumerate(candles),
        key=lambda item: (item[1].instrument_id, item[1].timestamp),
    )


def calculate_vwap(
    candles: list[MarketCandle],
) -> list[Decimal | None]:
    """Calculate cumulative VWAP, resetting at each Indian trading date."""

    results: list[Decimal | None] = [None] * len(candles)
    state: dict[tuple[str, date], tuple[Decimal, int]] = {}

    for index, candle in _ordered_candles(candles):
        key = (candle.instrument_id, candle.timestamp.astimezone(IST).date())

        if candle.volume is None:
            continue

        typical_price = (
            candle.high + candle.low + candle.close
        ) / Decimal("3")

        pv, volume = state.get(key, (Decimal("0"), 0))
        pv += typical_price * candle.volume
        volume += candle.volume
        state[key] = (pv, volume)

        if volume > 0:
            results[index] = pv / Decimal(volume)

    return results


def calculate_atr(
    candles: list[MarketCandle],
    period: int = 14,
) -> list[Decimal | None]:
    """Calculate ATR using Wilder's smoothing, independently per instrument."""

    if period < 1:
        raise ValueError("period must be greater than zero")

    results: list[Decimal | None] = [None] * len(candles)
    grouped: dict[str, list[tuple[int, MarketCandle]]] = defaultdict(list)

    for item in _ordered_candles(candles):
        grouped[item[1].instrument_id].append(item)

    decimal_period = Decimal(period)

    for instrument_candles in grouped.values():
        previous_close = None
        true_ranges: list[Decimal] = []
        current_atr = None

        for index, candle in instrument_candles:
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

            results[index] = current_atr

    return results


def calculate_historical_volatility(
    candles: list[MarketCandle],
    period: int = 20,
    annualization_factor: int = 252,
) -> list[Decimal | None]:
    """Calculate rolling annualized historical volatility from log returns."""

    if period < 2:
        raise ValueError("period must be at least 2")

    if annualization_factor < 1:
        raise ValueError("annualization_factor must be greater than zero")

    results: list[Decimal | None] = [None] * len(candles)
    grouped: dict[str, list[tuple[int, MarketCandle]]] = defaultdict(list)

    for item in _ordered_candles(candles):
        grouped[item[1].instrument_id].append(item)

    annualization = Decimal(annualization_factor).sqrt()

    for instrument_candles in grouped.values():
        returns: list[Decimal] = []
        previous_close = None

        for index, candle in instrument_candles:
            if previous_close is None:
                previous_close = candle.close
                continue

            if previous_close <= 0 or candle.close <= 0:
                raise ValueError("Close prices must be positive")

            log_return = (candle.close / previous_close).ln()
            returns.append(log_return)
            previous_close = candle.close

            if len(returns) < period:
                continue

            window = returns[-period:]
            mean = sum(window, Decimal("0")) / Decimal(period)

            variance = sum(
                ((value - mean) ** 2 for value in window),
                Decimal("0"),
            ) / Decimal(period - 1)

            results[index] = variance.sqrt() * annualization

    return results
