
from pathlib import Path

from quantedge.market_data.csv_reader import load_candles
from quantedge.market_data.parquet_store import write_candles


def run_csv_to_parquet_pipeline(
    csv_path: str | Path,
    parquet_path: str | Path,
) -> int:
    """
    Ingest historical market data from CSV,
    validate candles and persist them as Parquet.

    Returns:
        Number of candles successfully persisted.
    """

    # Step 1: Read CSV and validate each candle.
    candles = load_candles(csv_path)

    if not candles:
        raise ValueError("No valid candles found in CSV file")

    # Step 2: Persist validated candles.
    write_candles(candles, parquet_path)

    return len(candles)
