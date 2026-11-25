
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from quantedge.market_data.models import MarketCandle


IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True, slots=True)
class DailyOHLCV:
    instrument_id: str
    trading_date: date
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int | None
    candle_count: int


def aggregate_daily_ohlcv(
    candles: list[MarketCandle],
) -> list[DailyOHLCV]:
    """
    Aggregate intraday candles into daily OHLCV records.

    Trading dates are determined using Asia/Kolkata timezone.

    Volume policy:
    - Sum volumes when every candle has a volume value.
    - Return None when any candle has missing volume.
    - Preserve zero-volume candles in the aggregation.
    """

    grouped: dict[tuple[str, date, str], list[MarketCandle]] = defaultdict(list)

    for candle in candles:
        trading_date = candle.timestamp.astimezone(IST).date()

        key = (
            candle.instrument_id,
            trading_date,
            candle.timeframe.value,
        )
        grouped[key].append(candle)

    daily_records: list[DailyOHLCV] = []

    for (instrument_id, trading_date, timeframe), group in sorted(
        grouped.items(),
        key=lambda item: item[0],
    ):
        ordered = sorted(group, key=lambda candle: candle.timestamp)

        volumes = [candle.volume for candle in ordered]

        daily_volume = (
            sum(volumes)
            if all(volume is not None for volume in volumes)
            else None
        )

        daily_records.append(
            DailyOHLCV(
                instrument_id=instrument_id,
                trading_date=trading_date,
                timeframe=timeframe,
                open=ordered[0].open,
                high=max(candle.high for candle in ordered),
                low=min(candle.low for candle in ordered),
                close=ordered[-1].close,
                volume=daily_volume,
                candle_count=len(ordered),
            )
        )

    return daily_records
