
import csv
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quantedge.market_data.pipeline import run_csv_to_parquet_pipeline
from quantedge.market_data.parquet_store import read_candles


def create_csv(path, rows):
    fieldnames = [
        "instrument_id",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def valid_row(minute, **overrides):
    row = {
        "instrument_id": "NIFTY",
        "timestamp": f"2026-11-25T10:{minute:02d}:00+05:30",
        "open": "100",
        "high": "105",
        "low": "95",
        "close": "102",
        "volume": "1000",
    }
    row.update(overrides)
    return row


def test_pipeline_persists_valid_candles(tmp_path):
    csv_path = tmp_path / "market_data.csv"
    parquet_path = tmp_path / "market_data.parquet"

    create_csv(csv_path, [
        valid_row(0),
        valid_row(1),
        valid_row(2),
    ])

    count = run_csv_to_parquet_pipeline(
        csv_path,
        parquet_path,
    )

    assert count == 3
    assert parquet_path.exists()

    candles = read_candles(parquet_path)

    assert len(candles) == 3
    assert candles[0].instrument_id == "NIFTY"
    assert candles[0].open == Decimal("100")
    assert candles[0].volume == 1000
    assert candles[0].timestamp == datetime(
        2026, 11, 25, 4, 30,
        tzinfo=timezone.utc,
    )


def test_pipeline_rejects_empty_csv(tmp_path):
    csv_path = tmp_path / "empty.csv"
    parquet_path = tmp_path / "output.parquet"

    create_csv(csv_path, [])

    with pytest.raises(
        ValueError,
        match="No valid candles found",
    ):
        run_csv_to_parquet_pipeline(
            csv_path,
            parquet_path,
        )

    assert not parquet_path.exists()


def test_pipeline_rejects_duplicate_candles(tmp_path):
    csv_path = tmp_path / "duplicate.csv"
    parquet_path = tmp_path / "output.parquet"

    row = valid_row(0)

    create_csv(csv_path, [row, row.copy()])

    with pytest.raises(
        ValueError,
        match="DUPLICATE_TIMESTAMP",
    ):
        run_csv_to_parquet_pipeline(
            csv_path,
            parquet_path,
        )

    assert not parquet_path.exists()


def test_pipeline_rejects_mixed_instruments(tmp_path):
    csv_path = tmp_path / "mixed.csv"
    parquet_path = tmp_path / "output.parquet"

    create_csv(csv_path, [
        valid_row(0, instrument_id="NIFTY"),
        valid_row(1, instrument_id="BANKNIFTY"),
    ])

    with pytest.raises(
        ValueError,
        match="MIXED_INSTRUMENTS",
    ):
        run_csv_to_parquet_pipeline(
            csv_path,
            parquet_path,
        )

    assert not parquet_path.exists()


def test_pipeline_rejects_out_of_order_candles(tmp_path):
    csv_path = tmp_path / "out_of_order.csv"
    parquet_path = tmp_path / "output.parquet"

    create_csv(csv_path, [
        valid_row(2),
        valid_row(1),
    ])

    with pytest.raises(
        ValueError,
        match="OUT_OF_ORDER",
    ):
        run_csv_to_parquet_pipeline(
            csv_path,
            parquet_path,
        )

    assert not parquet_path.exists()


def test_pipeline_persists_candles_with_missing_interval_warning(
    tmp_path,
):
    csv_path = tmp_path / "missing_interval.csv"
    parquet_path = tmp_path / "output.parquet"

    create_csv(csv_path, [
        valid_row(0),
        valid_row(2),
    ])

    count = run_csv_to_parquet_pipeline(
        csv_path,
        parquet_path,
    )

    assert count == 2
    assert parquet_path.exists()

    candles = read_candles(parquet_path)

    assert len(candles) == 2



def test_pipeline_returns_quality_report(tmp_path):
    csv_path = tmp_path / "quality.csv"
    parquet_path = tmp_path / "quality.parquet"

    create_csv(csv_path, [
        valid_row(0),
        valid_row(2),
    ])

    result = run_csv_to_parquet_pipeline(
        csv_path,
        parquet_path,
        return_report=True,
    )

    assert result.candle_count == 2
    assert result.quality_report.candle_count == 2
    assert result.quality_report.is_clean
    assert any(
        issue.code == "MISSING_INTERVAL"
        for issue in result.quality_report.issues
    )
    assert parquet_path.exists()
