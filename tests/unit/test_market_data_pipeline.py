
from quantedge.market_data.pipeline import run_csv_to_parquet_pipeline
from quantedge.market_data.parquet_store import read_candles


def test_csv_to_parquet_pipeline(tmp_path):
    csv_path = tmp_path / "sample.csv"
    parquet_path = tmp_path / "processed" / "market_data.parquet"

    csv_path.write_text(
        "instrument_id,timestamp,timeframe,open,high,low,close,volume\n"
        "QE-FUT-001,2026-11-18T03:45:00+00:00,1m,"
        "25100,25115,25095,25110,12500\n"
        "QE-FUT-001,2026-11-18T03:46:00+00:00,1m,"
        "25110,25120,25105,25115,11800\n",
        encoding="utf-8",
    )

    count = run_csv_to_parquet_pipeline(csv_path, parquet_path)

    restored = read_candles(parquet_path)

    assert count == 2
    assert len(restored) == 2
    assert restored[0].close == 25110
    assert restored[1].close == 25115
