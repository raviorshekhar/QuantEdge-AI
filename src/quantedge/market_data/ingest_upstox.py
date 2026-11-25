
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import Instrument, InstrumentStatus
from quantedge.market_data.models import CandleTimeframe, MarketCandle
from quantedge.market_data.parquet_store import write_candles
from quantedge.market_data.providers.upstox import (
    UpstoxHistoricalClient,
    create_upstox_client,
)
from quantedge.market_data.providers.upstox_instruments import (
    UpstoxInstrumentMasterLoader,
)
from quantedge.market_data.quality import (
    QualityReport,
    Severity,
    validate_candles,
)


IST = ZoneInfo("Asia/Kolkata")

NIFTY_INDEX_ID = "NSE-INDEX-NIFTY50"

MAX_CHUNK_DAYS = 30


class IngestionError(RuntimeError):
    """Raised when market-data ingestion cannot complete safely."""


@dataclass(frozen=True)
class IngestionResult:
    instrument_id: str
    expiry_date: date
    candle_count: int
    from_date: date
    to_date: date
    output_path: Path
    quality_report: QualityReport


# -------------------------------------------------
# 1. Date range utilities
# -------------------------------------------------

def split_date_range(
    from_date: date,
    to_date: date,
    max_days: int = MAX_CHUNK_DAYS,
) -> list[tuple[date, date]]:
    """Split an inclusive date range into API-safe chunks."""

    if from_date > to_date:
        raise ValueError("from_date cannot be after to_date")

    if max_days < 1:
        raise ValueError("max_days must be positive")

    chunks: list[tuple[date, date]] = []

    current = from_date

    while current <= to_date:
        chunk_end = min(
            current + timedelta(days=max_days - 1),
            to_date,
        )

        chunks.append((current, chunk_end))

        current = chunk_end + timedelta(days=1)

    return chunks


# -------------------------------------------------
# 2. Instrument selection
# -------------------------------------------------

def select_nearest_nifty_future(
    master: InstrumentMaster,
    as_of: date,
) -> Instrument:
    """Select the nearest unexpired NIFTY futures contract."""

    futures = master.get_futures_by_underlying(
        underlying_id=NIFTY_INDEX_ID,
        status=InstrumentStatus.ACTIVE,
        as_of=as_of,
    )

    eligible = [
        future
        for future in futures
        if future.expiry_date is not None
        and future.expiry_date >= as_of
    ]

    if not eligible:
        raise IngestionError(
            f"No active NIFTY futures contract found as of {as_of}"
        )

    eligible.sort(
        key=lambda future: (
            future.expiry_date,
            future.instrument_id,
        )
    )

    return eligible[0]


# -------------------------------------------------
# 3. Historical + intraday fetching
# -------------------------------------------------

def fetch_candles_for_range(
    client: UpstoxHistoricalClient,
    master: InstrumentMaster,
    instrument_id: str,
    as_of: date,
    from_date: date,
    to_date: date,
) -> list[MarketCandle]:
    """
    Fetch completed historical dates and current-day intraday candles.

    Historical API is used for dates strictly before as_of.
    Intraday API is used for as_of only.
    """

    if from_date > to_date:
        raise ValueError("from_date cannot be after to_date")

    if to_date > as_of:
        raise ValueError(
            "to_date cannot be after the current instrument snapshot date"
        )

    all_candles: list[MarketCandle] = []

    # Historical candles: completed dates.

    historical_end = min(
        to_date,
        as_of - timedelta(days=1),
    )

    if from_date <= historical_end:
        chunks = split_date_range(
            from_date=from_date,
            to_date=historical_end,
        )

        for chunk_start, chunk_end in chunks:
            print(
                f"Fetching historical candles: "
                f"{chunk_start} to {chunk_end}"
            )

            candles = client.fetch_instrument_candles(
                instrument_master=master,
                instrument_id=instrument_id,
                as_of=as_of,
                from_date=chunk_start,
                to_date=chunk_end,
            )

            print(
                f"Historical candles received: {len(candles)}"
            )

            all_candles.extend(candles)

    # Current-day candles: intraday API.

    if from_date <= as_of <= to_date:
        print(
            f"Fetching current-day intraday candles: {as_of}"
        )

        intraday_candles = (
            client.fetch_instrument_intraday_candles(
                instrument_master=master,
                instrument_id=instrument_id,
                as_of=as_of,
            )
        )

        print(
            f"Intraday candles received: {len(intraday_candles)}"
        )

        all_candles.extend(intraday_candles)

    # Sort combined candles chronologically.

    all_candles.sort(
        key=lambda candle: candle.timestamp
    )

    return all_candles


# -------------------------------------------------
# 4. Ingestion boundary validation
# -------------------------------------------------

def validate_ingestion_candles(
    candles: list[MarketCandle],
    instrument_id: str,
    from_date: date,
    to_date: date,
) -> None:
    """
    Validate that received candles belong to the requested dataset.

    This validates instrument, timeframe and every candle's
    local exchange date. It does not determine exchange holidays
    or special trading sessions.
    """

    if not candles:
        raise IngestionError(
            "Upstox returned zero candles."
        )

    unexpected_instruments = {
        candle.instrument_id
        for candle in candles
        if candle.instrument_id != instrument_id
    }

    if unexpected_instruments:
        raise IngestionError(
            f"Unexpected instruments received: "
            f"{unexpected_instruments}"
        )

    unexpected_timeframes = {
        candle.timeframe
        for candle in candles
        if candle.timeframe != CandleTimeframe.ONE_MINUTE
    }

    if unexpected_timeframes:
        raise IngestionError(
            f"Unexpected candle timeframes received: "
            f"{unexpected_timeframes}"
        )

    out_of_range = []

    for candle in candles:
        candle_date = candle.timestamp.astimezone(IST).date()

        if candle_date < from_date or candle_date > to_date:
            out_of_range.append(
                (candle.instrument_id, candle.timestamp)
            )

    if out_of_range:
        raise IngestionError(
            f"{len(out_of_range)} candle(s) have timestamps "
            f"outside requested range {from_date} to {to_date}. "
            f"Examples: {out_of_range[:5]}"
        )

    # The combined dataset must be chronologically ordered.

    for previous, current in zip(candles, candles[1:]):
        if current.timestamp < previous.timestamp:
            raise IngestionError(
                "Candles are not chronologically ordered: "
                f"{current.timestamp} occurs before "
                f"{previous.timestamp}"
            )


# -------------------------------------------------
# 5. Quality report
# -------------------------------------------------

def print_quality_report(
    quality_report: QualityReport,
) -> None:
    """Print a concise summary of data quality issues."""

    errors = quality_report.errors
    warnings = quality_report.warnings

    print("\n--- QUALITY REPORT ---")

    print(
        f"Received candles: {quality_report.candle_count}"
    )

    print(f"Quality errors: {len(errors)}")
    print(f"Quality warnings: {len(warnings)}")

    if quality_report.issues:
        issue_counts = Counter(
            (
                issue.severity.value,
                issue.code,
            )
            for issue in quality_report.issues
        )

        print("\nIssue breakdown:")

        for (severity, code), count in sorted(
            issue_counts.items()
        ):
            print(
                f"[{severity}] {code}: {count}"
            )

        print("\nIssue details:")

        for issue in quality_report.issues:
            print(
                f"[{issue.severity.value}] "
                f"{issue.code}: {issue.message}"
            )

    else:
        print("No quality issues detected.")

    print("----------------------\n")


# -------------------------------------------------
# 6. Main ingestion workflow
# -------------------------------------------------

def run_ingestion(
    from_date: date,
    to_date: date,
    output_path: str | Path | None = None,
    *,
    as_of: date | None = None,
    loader: UpstoxInstrumentMasterLoader | None = None,
    client_factory: Callable[
        [], UpstoxHistoricalClient
    ] = create_upstox_client,
) -> IngestionResult:
    """
    Download, validate and persist NIFTY futures candles.

    Historical dates use Historical Candle V3.
    Current date uses Intraday Candle V3.

    Existing output files are never overwritten.
    """

    # Validate requested dates.

    if from_date > to_date:
        raise ValueError(
            "from_date cannot be after to_date"
        )

    effective_as_of = (
        as_of or datetime.now(IST).date()
    )

    if to_date > effective_as_of:
        raise ValueError(
            "to_date cannot be in the future relative "
            "to the instrument snapshot"
        )

    # -------------------------------------------------
    # 1. Download instrument master
    # -------------------------------------------------

    instrument_loader = (
        loader or UpstoxInstrumentMasterLoader()
    )

    print("Downloading Upstox NSE instrument master...")

    try:
        records = instrument_loader.download()

    finally:
        close_loader = getattr(
            instrument_loader,
            "close",
            None,
        )

        if callable(close_loader):
            close_loader()

    if not records:
        raise IngestionError(
            "Upstox instrument master returned no records"
        )

    # -------------------------------------------------
    # 2. Register instruments and provider mappings
    # -------------------------------------------------

    master = InstrumentMaster()

    print("Registering NIFTY 50 instruments...")

    instrument_loader.register_into(
        records=records,
        master=master,
        as_of=effective_as_of,
    )

    # -------------------------------------------------
    # 3. Select nearest active NIFTY future
    # -------------------------------------------------

    future = select_nearest_nifty_future(
        master=master,
        as_of=effective_as_of,
    )

    print(f"Selected contract: {future.symbol}")
    print(f"Instrument ID: {future.instrument_id}")
    print(f"Expiry: {future.expiry_date}")
    print(f"Lot size: {future.lot_size}")
    print(f"Tick size: {future.tick_size}")

    # -------------------------------------------------
    # 4. Resolve output path
    # -------------------------------------------------

    if output_path is None:
        output_path = (
            Path("data/market_data/upstox")
            / (
                f"{future.instrument_id}_1m_"
                f"{from_date}_{to_date}.parquet"
            )
        )

    destination = Path(output_path)

    if destination.exists():
        raise FileExistsError(
            f"Output already exists: {destination}. "
            "Choose another path or move the existing file."
        )

    # -------------------------------------------------
    # 5. Fetch historical + intraday candles
    # -------------------------------------------------

    print("Connecting to Upstox API...")

    with client_factory() as client:
        candles = fetch_candles_for_range(
            client=client,
            master=master,
            instrument_id=future.instrument_id,
            as_of=effective_as_of,
            from_date=from_date,
            to_date=to_date,
        )

    # -------------------------------------------------
    # 6. Validate received candle boundaries
    # -------------------------------------------------

    validate_ingestion_candles(
        candles=candles,
        instrument_id=future.instrument_id,
        from_date=from_date,
        to_date=to_date,
    )

    # -------------------------------------------------
    # 7. Run market-data quality validation
    # -------------------------------------------------

    quality_report = validate_candles(candles)

    print_quality_report(quality_report)

    if quality_report.errors:
        raise IngestionError(
            f"Quality validation failed with "
            f"{len(quality_report.errors)} error(s). "
            "Parquet output was not written."
        )

    if quality_report.warnings:
        print(
            f"Proceeding with {len(quality_report.warnings)} "
            "quality warning(s). Raw candle data will be preserved."
        )

    # -------------------------------------------------
    # 8. Persist validated candles
    # -------------------------------------------------

    try:
        write_candles(
            candles=candles,
            file_path=destination,
        )

    except FileExistsError:
        raise

    except Exception as exc:
        raise IngestionError(
            f"Unable to persist Parquet output: {exc}"
        ) from exc

    # -------------------------------------------------
    # 9. Return ingestion result
    # -------------------------------------------------

    return IngestionResult(
        instrument_id=future.instrument_id,
        expiry_date=future.expiry_date,
        candle_count=len(candles),
        from_date=from_date,
        to_date=to_date,
        output_path=destination,
        quality_report=quality_report,
    )


# -------------------------------------------------
# 7. CLI entry point
# -------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest NIFTY futures historical and "
            "current-day intraday candles from Upstox."
        )
    )

    parser.add_argument(
        "--from-date",
        required=True,
        type=date.fromisoformat,
        help="Start date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--to-date",
        required=True,
        type=date.fromisoformat,
        help="End date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Parquet output path",
    )

    args = parser.parse_args()

    try:
        result = run_ingestion(
            from_date=args.from_date,
            to_date=args.to_date,
            output_path=args.output,
        )

    except Exception as exc:
        parser.exit(
            1,
            f"\nINGESTION FAILED: {exc}\n",
        )

    print("\n========== INGESTION SUCCESSFUL ==========")

    print(f"Instrument: {result.instrument_id}")
    print(f"Expiry: {result.expiry_date}")
    print(
        f"Period: {result.from_date} to {result.to_date}"
    )
    print(f"Candles: {result.candle_count}")
    print(f"Output: {result.output_path}")

    print(
        f"Quality errors: "
        f"{result.quality_report.error_count}"
    )

    print(
        f"Quality warnings: "
        f"{result.quality_report.warning_count}"
    )

    print("===========================================")


if __name__ == "__main__":
    main()
