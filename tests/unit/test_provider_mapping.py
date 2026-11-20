
from datetime import date

import pytest
from pydantic import ValidationError

from quantedge.instruments.provider_mapping import (
    InstrumentProviderMapping,
)


def test_create_valid_provider_mapping():
    mapping = InstrumentProviderMapping(
        mapping_id="QE-MAP-001",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="123456",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
    )

    assert mapping.instrument_id == "QE-FUT-001"
    assert mapping.provider == "ProviderA"
    assert mapping.valid_to is None


def test_mapping_with_valid_date_range():
    mapping = InstrumentProviderMapping(
        mapping_id="QE-MAP-002",
        instrument_id="QE-FUT-001",
        provider="ProviderA",
        provider_instrument_id="123456",
        provider_symbol="NIFTY26NOVFUT",
        exchange="NSE",
        segment="NFO",
        valid_from=date(2026, 11, 1),
        valid_to=date(2026, 11, 30),
    )

    assert mapping.valid_to == date(2026, 11, 30)


def test_invalid_date_range_rejected():
    with pytest.raises(ValidationError):
        InstrumentProviderMapping(
            mapping_id="QE-MAP-003",
            instrument_id="QE-FUT-001",
            provider="ProviderA",
            provider_instrument_id="123456",
            provider_symbol="NIFTY26NOVFUT",
            exchange="NSE",
            segment="NFO",
            valid_from=date(2026, 11, 30),
            valid_to=date(2026, 11, 1),
        )


def test_missing_provider_id_rejected():
    with pytest.raises(ValidationError):
        InstrumentProviderMapping(
            mapping_id="QE-MAP-004",
            instrument_id="QE-FUT-001",
            provider="ProviderA",
            provider_symbol="NIFTY26NOVFUT",
            exchange="NSE",
            segment="NFO",
            valid_from=date(2026, 11, 1),
        )
