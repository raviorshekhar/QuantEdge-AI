
from datetime import date

import pytest
from pydantic import ValidationError

from quantedge.instruments.models import (
    Instrument,
    InstrumentType,
)


def test_create_nifty_index():
    instrument = Instrument(
        instrument_id="QE-INDEX-001",
        exchange="NSE",
        instrument_type=InstrumentType.INDEX,
        symbol="NIFTY 50",
        name="NIFTY 50 Index",
    )

    assert instrument.instrument_id == "QE-INDEX-001"
    assert instrument.instrument_type == InstrumentType.INDEX
    assert instrument.expiry_date is None


def test_create_nifty_future():
    instrument = Instrument(
        instrument_id="QE-FUT-001",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 11, 24),
    )

    assert instrument.instrument_type == InstrumentType.FUTURE
    assert instrument.underlying_id == "QE-INDEX-001"
    assert instrument.expiry_date == date(2026, 11, 24)


def test_future_without_expiry_rejected():
    with pytest.raises(ValidationError):
        Instrument(
            instrument_id="QE-FUT-002",
            exchange="NSE",
            instrument_type=InstrumentType.FUTURE,
            symbol="NIFTY",
            name="NIFTY Futures",
            underlying_id="QE-INDEX-001",
        )


def test_future_without_underlying_rejected():
    with pytest.raises(ValidationError):
        Instrument(
            instrument_id="QE-FUT-003",
            exchange="NSE",
            instrument_type=InstrumentType.FUTURE,
            symbol="NIFTY",
            name="NIFTY Futures",
            expiry_date=date(2026, 11, 24),
        )


def test_index_with_expiry_rejected():
    with pytest.raises(ValidationError):
        Instrument(
            instrument_id="QE-INDEX-002",
            exchange="NSE",
            instrument_type=InstrumentType.INDEX,
            symbol="NIFTY 50",
            name="NIFTY 50 Index",
            expiry_date=date(2026, 11, 24),
        )
