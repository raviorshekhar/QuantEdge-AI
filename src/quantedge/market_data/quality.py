
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from quantedge.market_data.models import MarketCandle


IST = ZoneInfo("Asia/Kolkata")


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class QualityIssue:
    severity: Severity
    code: str
    message: str


@dataclass(frozen=True)
class QualityReport:
    candle_count: int
    issues: tuple[QualityIssue, ...] = ()

    @property
    def errors(self) -> list[QualityIssue]:
        return [
            issue
            for issue in self.issues
            if issue.severity == Severity.ERROR
        ]

    @property
    def warnings(self) -> list[QualityIssue]:
        return [
            issue
            for issue in self.issues
            if issue.severity == Severity.WARNING
        ]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @property
    def is_clean(self) -> bool:
        """
        True when no ERROR-level issues exist.

        WARNING-level issues do not make the report unclean.
        """
        return not self.errors


def validate_candles(
    candles: list[MarketCandle],
) -> QualityReport:
    """
    Validate market candle integrity.

    Checks:
    - Instrument and timeframe consistency
    - Duplicate candle timestamps
    - Timestamp ordering
    - Intraday missing intervals
    - OHLC relationships
    - Positive prices
    - Negative, zero and missing volume

    Raw candle data is never modified or deleted.
    """

    issues: list[QualityIssue] = []

    if not candles:
        return QualityReport(candle_count=0)

    # -------------------------------------------------
    # 1. Instrument and timeframe consistency
    # -------------------------------------------------

    instruments = {
        candle.instrument_id
        for candle in candles
    }

    timeframes = {
        candle.timeframe
        for candle in candles
    }

    if len(instruments) > 1:
        issues.append(
            QualityIssue(
                Severity.ERROR,
                "MIXED_INSTRUMENTS",
                "File contains more than one instrument_id",
            )
        )

    if len(timeframes) > 1:
        issues.append(
            QualityIssue(
                Severity.ERROR,
                "MIXED_TIMEFRAMES",
                "File contains more than one timeframe",
            )
        )

    # -------------------------------------------------
    # 2. Duplicate candle detection
    # -------------------------------------------------

    candle_keys = Counter(
        (
            candle.instrument_id,
            candle.timestamp,
            candle.timeframe,
        )
        for candle in candles
    )

    duplicate_keys = {
        key: count
        for key, count in candle_keys.items()
        if count > 1
    }

    if duplicate_keys:
        duplicate_records = sum(
            count - 1
            for count in duplicate_keys.values()
        )

        issues.append(
            QualityIssue(
                Severity.ERROR,
                "DUPLICATE_TIMESTAMP",
                (
                    f"{len(duplicate_keys)} duplicate candle keys "
                    f"found; {duplicate_records} extra records"
                ),
            )
        )

    # -------------------------------------------------
    # 3. Individual candle validation
    # -------------------------------------------------

    for candle in candles:

        prices = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
        )

        if any(price <= 0 for price in prices):
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "INVALID_PRICE",
                    (
                        f"Non-positive OHLC price found for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        if candle.high < max(
            candle.open,
            candle.close,
            candle.low,
        ):
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "INVALID_HIGH",
                    (
                        f"High is below another OHLC value for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        if candle.low > min(
            candle.open,
            candle.close,
            candle.high,
        ):
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "INVALID_LOW",
                    (
                        f"Low is above another OHLC value for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        # Volume validation

        if candle.volume is None:
            issues.append(
                QualityIssue(
                    Severity.WARNING,
                    "MISSING_VOLUME",
                    (
                        f"Volume is unavailable for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        elif candle.volume < 0:
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "NEGATIVE_VOLUME",
                    (
                        f"Negative volume found for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        elif candle.volume == 0:
            issues.append(
                QualityIssue(
                    Severity.WARNING,
                    "ZERO_VOLUME",
                    (
                        f"Zero-volume candle found for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

        # Open interest validation

        if (
            candle.open_interest is not None
            and candle.open_interest < 0
        ):
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "NEGATIVE_OPEN_INTEREST",
                    (
                        f"Negative open interest found for "
                        f"{candle.instrument_id} at "
                        f"{candle.timestamp}"
                    ),
                )
            )

    # -------------------------------------------------
    # 4. Timestamp ordering and missing intervals
    # -------------------------------------------------

    previous_by_series: dict[
        tuple[str, object],
        MarketCandle,
    ] = {}

    for candle in candles:

        series_key = (
            candle.instrument_id,
            candle.timeframe,
        )

        previous = previous_by_series.get(series_key)

        if previous is None:
            previous_by_series[series_key] = candle
            continue

        if candle.timestamp < previous.timestamp:
            issues.append(
                QualityIssue(
                    Severity.ERROR,
                    "OUT_OF_ORDER",
                    (
                        f"Timestamp {candle.timestamp} occurs "
                        f"before previous timestamp "
                        f"{previous.timestamp}"
                    ),
                )
            )

            previous_by_series[series_key] = candle
            continue

        if candle.timestamp == previous.timestamp:
            previous_by_series[series_key] = candle
            continue

        interval_minutes = int(
            candle.timeframe.value[:-1]
        )

        expected_interval = timedelta(
            minutes=interval_minutes
        )

        actual_interval = (
            candle.timestamp - previous.timestamp
        )

        previous_date = (
            previous.timestamp.astimezone(IST).date()
        )

        current_date = (
            candle.timestamp.astimezone(IST).date()
        )

        # Detect intraday gaps only.
        # Overnight, weekends and market holidays are not
        # automatically treated as missing candle intervals.

        if (
            actual_interval > expected_interval
            and current_date == previous_date
        ):
            missing_minutes = (
                int(actual_interval.total_seconds() // 60)
                - interval_minutes
            )

            issues.append(
                QualityIssue(
                    Severity.WARNING,
                    "MISSING_INTERVAL",
                    (
                        f"Possible missing interval of "
                        f"{missing_minutes} minute(s) between "
                        f"{previous.timestamp} and "
                        f"{candle.timestamp}"
                    ),
                )
            )

        previous_by_series[series_key] = candle

    # -------------------------------------------------
    # 5. Final quality report
    # -------------------------------------------------

    return QualityReport(
        candle_count=len(candles),
        issues=tuple(issues),
    )
