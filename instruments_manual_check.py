
from datetime import date

from quantedge.instruments.models import (
    Instrument,
    InstrumentType,
)


# NIFTY 50 Index
nifty_index = Instrument(
    instrument_id="QE-INDEX-001",
    exchange="NSE",
    instrument_type=InstrumentType.INDEX,
    symbol="NIFTY 50",
    name="NIFTY 50 Index",
)

# NIFTY Futures - First expiry
nifty_future_1 = Instrument(
    instrument_id="QE-FUT-001",
    exchange="NSE",
    instrument_type=InstrumentType.FUTURE,
    symbol="NIFTY",
    name="NIFTY Futures",
    underlying_id="QE-INDEX-001",
    expiry_date=date(2026, 11, 24),
)

# NIFTY Futures - Second expiry
nifty_future_2 = Instrument(
    instrument_id="QE-FUT-002",
    exchange="NSE",
    instrument_type=InstrumentType.FUTURE,
    symbol="NIFTY",
    name="NIFTY Futures",
    underlying_id="QE-INDEX-001",
    expiry_date=date(2026, 12, 29),
)

print(nifty_index.model_dump())
print(nifty_future_1.model_dump())
print(nifty_future_2.model_dump())


from pydantic import ValidationError

try:
    invalid_future = Instrument(
        instrument_id="QE-FUT-003",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY Futures",
        underlying_id="QE-INDEX-001",
        # expiry_date intentionally missing
    )

except ValidationError as error:
    print("\nInvalid contract rejected successfully!")
    print(error)
