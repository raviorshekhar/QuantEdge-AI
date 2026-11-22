from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from quantedge.market_data.models import MarketCandle


PARQUET_SCHEMA = pa.schema(
    [
        pa.field("instrument_id", pa.string(), nullable=False),
        pa.field("timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("timeframe", pa.string(), nullable=False),
        pa.field("open", pa.decimal128(20, 4), nullable=False),
        pa.field("high", pa.decimal128(20, 4), nullable=False),
        pa.field("low", pa.decimal128(20, 4), nullable=False),
        pa.field("close", pa.decimal128(20, 4), nullable=False),
        pa.field("volume", pa.int64(), nullable=True),
    ]
)


def write_candles(
    candles: list[MarketCandle],
    file_path: str | Path,
) -> None:
    """Persist validated market candles into a Parquet file."""

    if not candles:
        raise ValueError("Cannot write an empty candle collection")

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = [
        {
            "instrument_id": candle.instrument_id,
            "timestamp": candle.timestamp,
            "timeframe": candle.timeframe.value,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]

    table = pa.Table.from_pylist(records, schema=PARQUET_SCHEMA)

    pq.write_table(table, path, compression="zstd")


def read_candles(file_path: str | Path) -> list[MarketCandle]:
    """Read Parquet records and reconstruct validated MarketCandle objects."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")

    table = pq.read_table(path)

    records = table.to_pylist()

    return [
        MarketCandle.model_validate(
            {
                **record,
                "timestamp": record["timestamp"],
            }
        )
        for record in records
    ]
