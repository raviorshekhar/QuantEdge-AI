
from pathlib import Path

from quantedge.market_data.csv_reader import load_candles

csv_path = Path("data/sample/nifty_futures_sample.csv")

candles = load_candles(csv_path)

print(f"Total candles loaded: {len(candles)}")

for candle in candles[:3]:
    print(candle)

print(f"Timestamp timezone: {candles[0].timestamp.tzinfo}")
print(f"Price type: {type(candles[0].close)}")
