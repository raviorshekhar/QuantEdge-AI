
from pathlib import Path
import os
import tempfile

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
        pa.field("open_interest", pa.int64(), nullable=True),
    ]
)


class ParquetStoreError(RuntimeError):
    """Raised when Parquet storage operations fail."""


def _validate_schema(
    schema: pa.Schema,
) -> None:
    """Validate that a Parquet file matches the expected schema."""

    actual_schema = schema.remove_metadata()

    expected_schema = PARQUET_SCHEMA.remove_metadata()

    if not actual_schema.equals(
        expected_schema,
        check_metadata=False,
    ):
        raise ParquetStoreError(
            "Parquet schema mismatch.\n"
            f"Expected:\n{expected_schema}\n"
            f"Received:\n{actual_schema}"
        )


def _records_to_candles(
    records: list[dict],
) -> list[MarketCandle]:
    """Convert Parquet records into validated MarketCandle objects."""

    candles = []

    for index, record in enumerate(records):
        try:
            candle = MarketCandle.model_validate(record)

        except Exception as exc:
            raise ParquetStoreError(
                f"Unable to reconstruct candle at row {index}: {exc}"
            ) from exc

        candles.append(candle)

    return candles


def _read_table(
    file_path: Path,
) -> pa.Table:
    """Read and schema-validate a Parquet file."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Parquet file not found: {file_path}"
        )

    if not file_path.is_file():
        raise ParquetStoreError(
            f"Parquet path is not a file: {file_path}"
        )

    try:
        table = pq.read_table(file_path)

    except Exception as exc:
        raise ParquetStoreError(
            f"Unable to read Parquet file: {file_path}"
        ) from exc

    _validate_schema(table.schema)

    return table


def write_candles(
    candles: list[MarketCandle],
    file_path: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """
    Persist validated market candles into a Parquet file.

    Writes through a temporary file and verifies the output
    before publishing it at the destination.

    Existing files are protected by default.

    Set overwrite=True only when intentional replacement
    of an existing dataset is required.
    """

    if not candles:
        raise ValueError(
            "Cannot write an empty candle collection"
        )

    path = Path(file_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Parquet file already exists: {path}. "
            "Choose another path or explicitly use overwrite=True."
        )

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
            "open_interest": candle.open_interest,
        }
        for candle in candles
    ]

    try:
        table = pa.Table.from_pylist(
            records,
            schema=PARQUET_SCHEMA,
        )

    except Exception as exc:
        raise ParquetStoreError(
            "Unable to construct Parquet table from candles"
        ) from exc

    temporary_path = None

    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )

        temporary_path = Path(temporary_name)

        os.close(file_descriptor)

        # 1. Write temporary Parquet file.

        pq.write_table(
            table,
            temporary_path,
            compression="zstd",
        )

        # 2. Read back and validate schema.

        verification_table = _read_table(
            temporary_path,
        )

        if verification_table.num_rows != len(candles):
            raise ParquetStoreError(
                "Read-back row count does not match "
                "the original candle count"
            )

        # 3. Reconstruct models and verify round-trip integrity.

        verification_candles = _records_to_candles(
            verification_table.to_pylist()
        )

        if verification_candles != candles:
            raise ParquetStoreError(
                "Parquet read-back verification failed. "
                "Stored candle values differ from input values."
            )

        # 4. Publish the verified file.

        if overwrite:
            os.replace(
                temporary_path,
                path,
            )

        else:
            # Atomic no-overwrite publication.
            # os.link fails if another process creates the
            # destination after the initial existence check.

            os.link(
                temporary_path,
                path,
            )

    except FileExistsError:
        raise FileExistsError(
            f"Parquet file already exists: {path}. "
            "Existing data was not overwritten."
        ) from None

    except ParquetStoreError:
        raise

    except Exception as exc:
        raise ParquetStoreError(
            f"Unable to persist Parquet file: {path}"
        ) from exc

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


def read_candles(
    file_path: str | Path,
) -> list[MarketCandle]:
    """
    Read Parquet records and reconstruct validated MarketCandle objects.

    The stored schema is checked before reconstructing models.
    """

    path = Path(file_path)

    table = _read_table(path)

    return _records_to_candles(
        table.to_pylist()
    )
