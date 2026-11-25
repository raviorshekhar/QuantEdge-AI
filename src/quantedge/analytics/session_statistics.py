
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantedge.market_data.models import MarketCandle


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True, slots=True)
class SessionStatistics:
    instrument_id: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None
    candle_count: int
    price_range: Decimal
    change: Decimal
    change_percent: Decimal | None


def calculate_session_statistics(
    candles: list[MarketCandle],
) -> list[SessionStatistics]:
    """Calculate OHLCV and price statistics for each trading session."""

    grouped: dict[
        tuple[str, date],
        list[MarketCandle],
    ] = defaultdict(list)

    for candle in candles:
        trading_date = candle.timestamp.astimezone(IST).date()
        grouped[(candle.instrument_id, trading_date)].append(candle)

    results: list[SessionStatistics] = []

    for (instrument_id, trading_date), group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda candle: candle.timestamp)

        first = ordered[0]
        last = ordered[-1]

        high = max(candle.high for candle in ordered)
        low = min(candle.low for candle in ordered)

        volumes = [candle.volume for candle in ordered]

        total_volume = (
            sum(volumes)
            if all(volume is not None for volume in volumes)
            else None
        )

        change = last.close - first.open

        change_percent = (
            change / first.open * Decimal("100")
            if first.open != 0
            else None
        )

        results.append(
            SessionStatistics(
                instrument_id=instrument_id,
                trading_date=trading_date,
                open=first.open,
                high=high,
                low=low,
                close=last.close,
                volume=total_volume,
                candle_count=len(ordered),
                price_range=high - low,
                change=change,
                change_percent=change_percent,
            )
        )

    return results
