
import csv
from pathlib import Path

from pydantic import ValidationError

from quantedge.market_data.models import MarketCandle


class CSVIngestionError(ValueError):
    """Raised when CSV data cannot be ingested."""


REQUIRED_COLUMNS = {
    "instrument_id",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
}


def load_candles(file_path: str | Path) -> list[MarketCandle]:
    """
    Read historical market data from a CSV file
    and convert each valid row into a MarketCandle.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    if not path.is_file():
        raise CSVIngestionError(f"Path is not a file: {path}")

    candles: list[MarketCandle] = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise CSVIngestionError("CSV file is empty or has no header")

            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise CSVIngestionError("CSV contains duplicate column names")

            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)

            if missing_columns:
                raise CSVIngestionError(
                    f"Missing required columns: {sorted(missing_columns)}"
                )

            for row in reader:
                row_number = reader.line_num

                # Ignore completely empty rows.
                if not row or all(
                    value is None or not value.strip()
                    for value in row.values()
                ):
                    continue

                if None in row:
                    raise CSVIngestionError(
                        f"Row {row_number}: unexpected extra CSV fields"
                    )

                # Blank optional fields should use model defaults.
                if not row.get("timeframe"):
                    row.pop("timeframe", None)

                if not row.get("volume"):
                    row["volume"] = None

                if not row.get("open_interest"):
                    row["open_interest"] = None

                try:
                    candle = MarketCandle.model_validate(row)
                except ValidationError as exc:
                    raise CSVIngestionError(
                        f"Invalid market data at CSV row {row_number}: {exc}"
                    ) from exc

                candles.append(candle)

    except csv.Error as exc:
        raise CSVIngestionError(f"Unable to parse CSV: {exc}") from exc

    return candles
