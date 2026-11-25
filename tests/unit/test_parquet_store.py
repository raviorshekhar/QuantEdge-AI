
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from quantedge.market_data.models import MarketCandle
from quantedge.market_data.parquet_store import (
    read_candles,
    write_candles,
)


@pytest.fixture
def sample_candles():
    return [
        MarketCandle(
            instrument_id="QE-FUT-001",
            timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
            open=Decimal("25100.0000"),
            high=Decimal("25115.0000"),
            low=Decimal("25095.0000"),
            close=Decimal("25110.0000"),
            volume=12500,
            open_interest=185000,
        ),
        MarketCandle(
            instrument_id="QE-FUT-001",
            timestamp=datetime(2026, 11, 18, 3, 46, tzinfo=timezone.utc),
            open=Decimal("25110.0000"),
            high=Decimal("25120.0000"),
            low=Decimal("25105.0000"),
            close=Decimal("25115.0000"),
            volume=11800,
            open_interest=185250,
        ),
    ]


def test_parquet_round_trip(tmp_path, sample_candles):
    file_path = tmp_path / "market_data.parquet"

    write_candles(sample_candles, file_path)
    restored = read_candles(file_path)

    assert restored == sample_candles


def test_write_creates_parent_directories(tmp_path, sample_candles):
    file_path = tmp_path / "processed" / "market_data.parquet"

    write_candles(sample_candles, file_path)

    assert file_path.exists()


def test_write_empty_candles_raises_error(tmp_path):
    file_path = tmp_path / "empty.parquet"

    with pytest.raises(ValueError, match="empty candle collection"):
        write_candles([], file_path)


def test_read_missing_file_raises_error(tmp_path):
    file_path = tmp_path / "missing.parquet"

    with pytest.raises(FileNotFoundError):
        read_candles(file_path)


def test_parquet_preserves_open_interest(tmp_path):
    file_path = tmp_path / "market_data_oi.parquet"

    candle = MarketCandle(
        instrument_id="QE-FUT-001",
        timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
        open=Decimal("25100.0000"),
        high=Decimal("25115.0000"),
        low=Decimal("25095.0000"),
        close=Decimal("25110.0000"),
        volume=12500,
        open_interest=185000,
    )

    write_candles([candle], file_path)
    restored = read_candles(file_path)

    assert len(restored) == 1
    assert restored[0].open_interest == 185000
    assert restored[0] == candle


def test_parquet_preserves_missing_open_interest(tmp_path):
    file_path = tmp_path / "market_data_no_oi.parquet"

    candle = MarketCandle(
        instrument_id="QE-FUT-001",
        timestamp=datetime(2026, 11, 18, 3, 45, tzinfo=timezone.utc),
        open=Decimal("25100.0000"),
        high=Decimal("25115.0000"),
        low=Decimal("25095.0000"),
        close=Decimal("25110.0000"),
        volume=12500,
    )

    write_candles([candle], file_path)
    restored = read_candles(file_path)

    assert restored[0].open_interest is None
