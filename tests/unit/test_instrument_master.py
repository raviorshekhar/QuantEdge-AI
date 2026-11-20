
from datetime import date

import pytest

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import Instrument, InstrumentType
from quantedge.instruments.provider_mapping import InstrumentProviderMapping


@pytest.fixture
def instrument_master():
    return InstrumentMaster()


@pytest.fixture
def nifty_index():
    return Instrument(
        instrument_id="QE-INDEX-001",
        exchange="NSE",
        instrument_type=InstrumentType.INDEX,
        symbol="NIFTY 50",
        name="NIFTY 50 Index",
    )


@pytest.fixture
def nifty_future():
    return Instrument(
        instrument_id="QE-FUT-001",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 11, 24),
    )


@pytest.fixture
def provider_mapping():
    return InstrumentProviderMapping(
        mapping_id="QE-MAP-001",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="123456",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )


def test_register_index(instrument_master, nifty_index):
    instrument_master.register_instrument(nifty_index)

    assert instrument_master.get_instrument("QE-INDEX-001") == nifty_index


def test_duplicate_instrument_rejected(instrument_master, nifty_index):
    instrument_master.register_instrument(nifty_index)

    with pytest.raises(ValueError, match="Instrument ID already exists"):
        instrument_master.register_instrument(nifty_index)


def test_future_without_registered_underlying_rejected(
    instrument_master, nifty_future
):
    with pytest.raises(ValueError, match="Underlying instrument does not exist"):
        instrument_master.register_instrument(nifty_future)


def test_register_future_with_existing_underlying(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    assert instrument_master.get_instrument("QE-FUT-001") == nifty_future


def test_mapping_without_registered_instrument_rejected(
    instrument_master, provider_mapping
):
    with pytest.raises(ValueError, match="Referenced instrument does not exist"):
        instrument_master.register_mapping(provider_mapping)


def test_register_provider_mapping(
    instrument_master, nifty_index, nifty_future, provider_mapping
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)
    instrument_master.register_mapping(provider_mapping)

    assert instrument_master.get_mapping("QE-MAP-001") == provider_mapping


def test_duplicate_mapping_id_rejected(
    instrument_master, nifty_index, nifty_future, provider_mapping
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)
    instrument_master.register_mapping(provider_mapping)

    with pytest.raises(ValueError, match="Mapping ID already exists"):
        instrument_master.register_mapping(provider_mapping)
