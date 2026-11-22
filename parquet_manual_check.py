from pathlib import Path

from quantedge.market_data.csv_reader import load_candles
from quantedge.market_data.parquet_store import (
    read_candles,
    write_candles,
)

csv_path = Path("data/sample/nifty_futures_sample.csv")
parquet_path = Path("data/processed/nifty_futures_sample.parquet")

# Step 1: Load and validate CSV
candles = load_candles(csv_path)

# Step 2: Write Parquet
write_candles(candles, parquet_path)

# Step 3: Read Parquet
restored_candles = read_candles(parquet_path)

print(f"Original candles: {len(candles)}")
print(f"Restored candles: {len(restored_candles)}")
print(f"Parquet file exists: {parquet_path.exists()}")

# Verify data integrity
assert len(candles) == len(restored_candles)

for original, restored in zip(candles, restored_candles):
    assert original == restored

print("Parquet round-trip verification: PASSED")
