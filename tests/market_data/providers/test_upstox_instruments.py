
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import InstrumentStatus, InstrumentType
from quantedge.market_data.providers.upstox_instruments import (
    UpstoxInstrumentError,
    UpstoxInstrumentMasterLoader,
)


AS_OF = date(2026, 11, 25)


def epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


@pytest.fixture
def upstox_records():
    ist = ZoneInfo("Asia/Kolkata")

    return [
        {
            "segment": "NSE_INDEX",
            "name": "NIFTY 50",
            "exchange": "NSE",
            "instrument_type": "INDEX",
            "instrument_key": "NSE_INDEX|Nifty 50",
            "trading_symbol": "Nifty 50",
        },
        {
            "segment": "NSE_FO",
            "name": "NIFTY FUT",
            "exchange": "NSE",
            "instrument_type": "FUT",
            "underlying_symbol": "NIFTY",
            "underlying_type": "INDEX",
            "underlying_key": "NSE_INDEX|Nifty 50",
            "instrument_key": "NSE_FO|FUT001",
            "trading_symbol": "NIFTY FUT 26 NOV 26",
            "expiry": epoch_ms(datetime(2026, 11, 26, 23, 59, tzinfo=ist)),
            "lot_size": 65,
            "tick_size": 0.05,
        },
        {
            "segment": "NSE_FO",
            "name": "NIFTY FUT",
            "exchange": "NSE",
            "instrument_type": "FUT",
            "underlying_symbol": "NIFTY",
            "underlying_type": "INDEX",
            "underlying_key": "NSE_INDEX|Nifty 50",
            "instrument_key": "NSE_FO|FUT002",
            "trading_symbol": "NIFTY FUT 31 DEC 26",
            "expiry": epoch_ms(datetime(2026, 12, 31, 23, 59, tzinfo=ist)),
            "lot_size": 65,
            "tick_size": 0.05,
        },
        {
            "segment": "NSE_FO",
            "name": "RELIANCE FUT",
            "exchange": "NSE",
            "instrument_type": "FUT",
            "underlying_symbol": "RELIANCE",
            "underlying_type": "EQUITY",
            "underlying_key": "NSE_EQ|RELIANCE",
            "instrument_key": "NSE_FO|RELIANCE001",
            "trading_symbol": "RELIANCE FUT",
            "expiry": epoch_ms(datetime(2026, 11, 26, 23, 59, tzinfo=ist)),
            "lot_size": 500,
            "tick_size": 0.05,
        },
    ]


def test_build_nifty_instruments(upstox_records):
    loader = UpstoxInstrumentMasterLoader()

    instruments, mappings = loader.build_instruments(
        upstox_records,
        AS_OF,
    )

    assert len(instruments) == 3
    assert len(mappings) == 3

    assert instruments[0].instrument_type == InstrumentType.INDEX
    assert instruments[0].symbol == "Nifty 50"

    assert all(
        instrument.instrument_type == InstrumentType.FUTURE
        for instrument in instruments[1:]
    )


def test_future_contract_metadata_is_preserved(upstox_records):
    loader = UpstoxInstrumentMasterLoader()

    instruments, _ = loader.build_instruments(
        upstox_records,
        AS_OF,
    )

    future = instruments[1]

    assert future.lot_size == 65
    assert str(future.tick_size) == "0.05"
    assert future.expiry_date == date(2026, 11, 26)
    assert future.underlying_id == "NSE-INDEX-NIFTY50"


def test_only_nifty_index_futures_are_selected(upstox_records):
    loader = UpstoxInstrumentMasterLoader()

    instruments, _ = loader.build_instruments(
        upstox_records,
        AS_OF,
    )

    assert len(instruments) == 3
    assert all(
        "NIFTY" in instrument.symbol.upper()
        for instrument in instruments[1:]
    )


def test_provider_mappings_are_created(upstox_records):
    loader = UpstoxInstrumentMasterLoader()

    _, mappings = loader.build_instruments(
        upstox_records,
        AS_OF,
    )

    future_mapping = mappings[1]

    assert future_mapping.provider == "UPSTOX"
    assert future_mapping.provider_instrument_id == "NSE_FO|FUT001"
    assert future_mapping.segment == "NSE_FO"


def test_register_into_instrument_master(upstox_records):
    loader = UpstoxInstrumentMasterLoader()
    master = InstrumentMaster()

    count = loader.register_into(
        upstox_records,
        master,
        AS_OF,
    )

    assert count == 3

    future = master.get_instrument(
        "NSE-FUT-NIFTY-20261126"
    )

    assert future is not None
    assert future.status == InstrumentStatus.ACTIVE

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id="NSE-FUT-NIFTY-20261126",
        as_of=AS_OF,
    )

    assert mapping is not None
    assert mapping.provider_instrument_id == "NSE_FO|FUT001"


def test_expired_future_is_marked_expired(upstox_records):
    loader = UpstoxInstrumentMasterLoader()

    records = upstox_records.copy()

    ist = ZoneInfo("Asia/Kolkata")
    records[1] = {
        **records[1],
        "expiry": epoch_ms(
            datetime(2026, 11, 20, 23, 59, tzinfo=ist)
        ),
    }

    instruments, _ = loader.build_instruments(records, AS_OF)

    expired_future = next(
        item
        for item in instruments
        if item.instrument_type == InstrumentType.FUTURE
        and item.expiry_date == date(2026, 11, 20)
    )

    assert expired_future.status == InstrumentStatus.EXPIRED


def test_missing_nifty_index_raises_error(upstox_records):
    records = [
        record
        for record in upstox_records
        if record.get("segment") != "NSE_INDEX"
    ]

    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="NIFTY 50 index"):
        loader.build_instruments(records, AS_OF)


def test_missing_nifty_futures_raises_error(upstox_records):
    records = upstox_records[:1]

    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="No NIFTY"):
        loader.build_instruments(records, AS_OF)


def test_invalid_lot_size_raises_error(upstox_records):
    records = upstox_records.copy()
    records[1] = {
        **records[1],
        "lot_size": 0,
    }

    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="lot size"):
        loader.build_instruments(records, AS_OF)


def test_duplicate_futures_key_raises_error(upstox_records):
    records = upstox_records + [upstox_records[1]]

    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="Duplicate"):
        loader.build_instruments(records, AS_OF)


def test_duplicate_expiry_raises_error(upstox_records):
    duplicate = {
        **upstox_records[2],
        "instrument_key": "NSE_FO|FUT003",
    }

    records = upstox_records + [duplicate]

    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="Duplicate"):
        loader.build_instruments(records, AS_OF)


def test_invalid_json_record_type_raises_error():
    loader = UpstoxInstrumentMasterLoader()

    with pytest.raises(UpstoxInstrumentError, match="must be a list"):
        loader.build_instruments({}, AS_OF)
