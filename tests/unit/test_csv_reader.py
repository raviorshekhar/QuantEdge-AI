
import csv

import pytest

from quantedge.market_data.csv_reader import (
    CSVIngestionError,
    load_candles,
)


@pytest.fixture
def sample_csv(tmp_path):
    file_path = tmp_path / "sample.csv"

    rows = [
        {
            "instrument_id": "QE-FUT-001",
            "timestamp": "2026-11-18T03:45:00+00:00",
            "timeframe": "1m",
            "open": "25100",
            "high": "25115",
            "low": "25095",
            "close": "25110",
            "volume": "12500",
        }
    ]

    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return file_path


def test_load_valid_csv(sample_csv):
    candles = load_candles(sample_csv)

    assert len(candles) == 1
    assert candles[0].instrument_id == "QE-FUT-001"
    assert candles[0].close == 25110
    assert candles[0].volume == 12500


def test_missing_required_column_raises_error(sample_csv):
    content = sample_csv.read_text()
    sample_csv.write_text(
        content.replace(",close", ""),
        encoding="utf-8",
    )

    with pytest.raises(CSVIngestionError, match="Missing required columns"):
        load_candles(sample_csv)


def test_invalid_ohlc_raises_error(sample_csv):
    content = sample_csv.read_text()
    content = content.replace("25115", "25000")
    sample_csv.write_text(content, encoding="utf-8")

    with pytest.raises(CSVIngestionError, match="Invalid market data"):
        load_candles(sample_csv)


def test_blank_volume_is_none(sample_csv):
    content = sample_csv.read_text()
    content = content.replace("12500", "")
    sample_csv.write_text(content, encoding="utf-8")

    candles = load_candles(sample_csv)

    assert candles[0].volume is None


def test_missing_file_raises_error(tmp_path):
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_candles(missing_file)
