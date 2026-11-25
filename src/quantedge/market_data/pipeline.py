
from dataclasses import dataclass
from pathlib import Path

from quantedge.market_data.csv_reader import load_candles
from quantedge.market_data.parquet_store import write_candles
from quantedge.market_data.quality import (
    QualityReport,
    validate_candles,
)


@dataclass(frozen=True)
class PipelineResult:
    candle_count: int
    quality_report: QualityReport


def run_csv_to_parquet_pipeline(
    csv_path: str | Path,
    parquet_path: str | Path,
    *,
    return_report: bool = False,
) -> int | PipelineResult:
    """
    Ingest CSV candles, validate dataset quality and persist
    candles to Parquet.

    Returns:
        Integer candle count by default.
        PipelineResult when return_report=True.
    """

    candles = load_candles(csv_path)

    if not candles:
        raise ValueError("No valid candles found in CSV file")

    report = validate_candles(candles)

    if report.errors:
        error_details = "; ".join(
            f"{issue.code}: {issue.message}"
            for issue in report.errors
        )
        raise ValueError(
            f"Market data quality validation failed: {error_details}"
        )

    write_candles(candles, parquet_path)

    result = PipelineResult(
        candle_count=len(candles),
        quality_report=report,
    )

    if return_report:
        return result

    return result.candle_count
