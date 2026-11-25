
from datetime import date

import pytest

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import Instrument, InstrumentType
from quantedge.instruments.provider_mapping import InstrumentProviderMapping
from decimal import Decimal

from quantedge.instruments.models import (
    Instrument,
    InstrumentStatus,
    InstrumentType,
)

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


# Existing InstrumentMaster tests

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


# New provider mapping overlap tests

def test_overlapping_mapping_period_rejected(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-101",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="101",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
        valid_to=date(2026, 11, 30),
    )

    overlapping = InstrumentProviderMapping(
        mapping_id="QE-MAP-102",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="102",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 15),
        valid_to=date(2026, 12, 15),
    )

    instrument_master.register_mapping(first)

    with pytest.raises(ValueError, match="validity periods cannot overlap"):
        instrument_master.register_mapping(overlapping)


def test_adjacent_mapping_periods_allowed(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-103",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="103",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
        valid_to=date(2026, 11, 30),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-104",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="104",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 12, 1),
        valid_to=date(2026, 12, 31),
    )

    instrument_master.register_mapping(first)
    instrument_master.register_mapping(second)

    assert instrument_master.get_mapping("QE-MAP-104") == second


def test_open_ended_mapping_blocks_future_overlap(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-105",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="105",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-106",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="106",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 12, 1),
    )

    instrument_master.register_mapping(first)

    with pytest.raises(ValueError, match="validity periods cannot overlap"):
        instrument_master.register_mapping(second)


def test_different_providers_can_map_same_instrument(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-107",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="107",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-108",
        instrument_id="QE-FUT-001",
        provider="ProviderB",
        provider_instrument_id="108",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    instrument_master.register_mapping(first)
    instrument_master.register_mapping(second)

    assert instrument_master.get_mapping("QE-MAP-108") == second


def test_different_instruments_can_have_overlapping_mappings(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    other_future = Instrument(
        instrument_id="QE-FUT-002",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY Futures Other",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
    )

    instrument_master.register_instrument(other_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-109",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="109",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-110",
        instrument_id="QE-FUT-002",
        provider="ProviderA",
        provider_instrument_id="110",
        provider_symbol="NIFTY26DECFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    instrument_master.register_mapping(first)
    instrument_master.register_mapping(second)

    assert instrument_master.get_mapping("QE-MAP-110") == second


def test_failed_overlapping_registration_does_not_modify_registry(
    instrument_master, nifty_index, nifty_future
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-111",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="111",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-112",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="112",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 12, 1),
    )

    instrument_master.register_mapping(first)

    with pytest.raises(ValueError, match="validity periods cannot overlap"):
        instrument_master.register_mapping(second)

    assert instrument_master.get_mapping("QE-MAP-112") is None




# Instrument metadata tests

def test_future_accepts_trading_metadata(nifty_index):
    future = Instrument(
        instrument_id="QE-FUT-META-001",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY Futures",
        underlying_id=nifty_index.instrument_id,
        expiry_date=date(2026, 11, 24),
        lot_size=65,
        tick_size=Decimal("0.05"),
    )

    assert future.lot_size == 65
    assert future.tick_size == Decimal("0.05")


def test_future_metadata_can_be_missing(nifty_future):
    assert nifty_future.lot_size is None
    assert nifty_future.tick_size is None


def test_zero_lot_size_rejected(nifty_index):
    with pytest.raises(ValueError):
        Instrument(
            instrument_id="QE-FUT-META-002",
            exchange="NSE",
            instrument_type=InstrumentType.FUTURE,
            symbol="NIFTY",
            name="NIFTY Futures",
            underlying_id=nifty_index.instrument_id,
            expiry_date=date(2026, 11, 24),
            lot_size=0,
        )


def test_zero_tick_size_rejected(nifty_index):
    with pytest.raises(ValueError):
        Instrument(
            instrument_id="QE-FUT-META-003",
            exchange="NSE",
            instrument_type=InstrumentType.FUTURE,
            symbol="NIFTY",
            name="NIFTY Futures",
            underlying_id=nifty_index.instrument_id,
            expiry_date=date(2026, 11, 24),
            tick_size=Decimal("0"),
        )


def test_index_cannot_have_lot_size():
    with pytest.raises(ValueError, match="index cannot have a lot_size"):
        Instrument(
            instrument_id="QE-INDEX-META-001",
            exchange="NSE",
            instrument_type=InstrumentType.INDEX,
            symbol="NIFTY 50",
            name="NIFTY 50 Index",
            lot_size=65,
        )


# Provider mapping resolver tests

def test_resolve_provider_instrument(
    instrument_master,
    nifty_index,
    nifty_future,
    provider_mapping,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)
    instrument_master.register_mapping(provider_mapping)

    resolved = instrument_master.resolve_provider_instrument(
        provider="ProviderA",
        provider_instrument_id="123456",
        as_of=date(2026, 11, 22),
    )

    assert resolved == nifty_future


def test_resolver_returns_none_for_unknown_provider(
    instrument_master,
    nifty_index,
    nifty_future,
    provider_mapping,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)
    instrument_master.register_mapping(provider_mapping)

    resolved = instrument_master.resolve_provider_instrument(
        provider="UnknownProvider",
        provider_instrument_id="123456",
        as_of=date(2026, 11, 22),
    )

    assert resolved is None


def test_resolver_returns_none_outside_mapping_validity(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    mapping = InstrumentProviderMapping(
        mapping_id="QE-MAP-201",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="201",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
        valid_to=date(2026, 11, 20),
    )

    instrument_master.register_mapping(mapping)

    resolved = instrument_master.resolve_provider_instrument(
        provider="ProviderA",
        provider_instrument_id="201",
        as_of=date(2026, 11, 21),
    )

    assert resolved is None


def test_resolver_supports_adjacent_historical_mappings(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-202",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="202",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
        valid_to=date(2026, 11, 15),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-203",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="203",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 16),
    )

    instrument_master.register_mapping(first)
    instrument_master.register_mapping(second)

    first_result = instrument_master.resolve_provider_instrument(
        "ProviderA",
        "202",
        date(2026, 11, 15),
    )

    second_result = instrument_master.resolve_provider_instrument(
        "ProviderA",
        "203",
        date(2026, 11, 16),
    )

    assert first_result == nifty_future
    assert second_result == nifty_future


def test_same_provider_instrument_id_cannot_map_to_two_instruments(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    other_future = Instrument(
        instrument_id="QE-FUT-OTHER",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="Another NIFTY Futures Contract",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
    )

    instrument_master.register_instrument(other_future)

    first = InstrumentProviderMapping(
        mapping_id="QE-MAP-204",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="DUPLICATE-ID",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    second = InstrumentProviderMapping(
        mapping_id="QE-MAP-205",
        instrument_id="QE-FUT-OTHER",
        provider="ProviderA",
        provider_instrument_id="DUPLICATE-ID",
        provider_symbol="NIFTY26DECFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    instrument_master.register_mapping(first)

    with pytest.raises(
        ValueError,
        match="Provider instrument ID validity periods cannot overlap",
    ):
        instrument_master.register_mapping(second)


# Futures discovery tests

def test_get_futures_by_underlying(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    december_future = Instrument(
        instrument_id="QE-FUT-DEC",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY December Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
    )

    instrument_master.register_instrument(december_future)

    futures = instrument_master.get_futures_by_underlying(
        underlying_id="QE-INDEX-001",
    )

    assert futures == [nifty_future, december_future]


def test_get_futures_filters_by_status(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    inactive_future = Instrument(
        instrument_id="QE-FUT-INACTIVE",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="Inactive NIFTY Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
        status=InstrumentStatus.INACTIVE,
    )

    instrument_master.register_instrument(inactive_future)

    futures = instrument_master.get_futures_by_underlying(
        underlying_id="QE-INDEX-001",
        status=InstrumentStatus.ACTIVE,
    )

    assert futures == [nifty_future]


def test_get_futures_filters_by_as_of_date(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    december_future = Instrument(
        instrument_id="QE-FUT-DEC",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY December Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
    )

    instrument_master.register_instrument(december_future)

    futures = instrument_master.get_futures_by_underlying(
        underlying_id="QE-INDEX-001",
        as_of=date(2026, 12, 1),
    )

    assert futures == [december_future]


def test_get_futures_filters_by_expiry_range(
    instrument_master,
    nifty_index,
    nifty_future,
):
    instrument_master.register_instrument(nifty_index)
    instrument_master.register_instrument(nifty_future)

    december_future = Instrument(
        instrument_id="QE-FUT-DEC",
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY",
        name="NIFTY December Futures",
        underlying_id="QE-INDEX-001",
        expiry_date=date(2026, 12, 31),
    )

    instrument_master.register_instrument(december_future)

    futures = instrument_master.get_futures_by_underlying(
        underlying_id="QE-INDEX-001",
        expiry_from=date(2026, 11, 25),
        expiry_to=date(2026, 12, 31),
    )

    assert futures == [december_future]


def test_invalid_expiry_range_rejected(instrument_master):
    with pytest.raises(
        ValueError,
        match="expiry_to cannot be earlier than expiry_from",
    ):
        instrument_master.get_futures_by_underlying(
            underlying_id="QE-INDEX-001",
            expiry_from=date(2026, 12, 31),
            expiry_to=date(2026, 11, 24),
        )
