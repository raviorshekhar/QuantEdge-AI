
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from quantedge.market_data.ingest_upstox import (
    IngestionError,
    select_nearest_nifty_future,
    split_date_range,
)


def test_split_date_range_single_window():
    chunks = split_date_range(
        date(2026, 11, 2),
        date(2026, 11, 25),
    )

    assert chunks == [
        (date(2026, 11, 2), date(2026, 11, 25))
    ]


def test_split_date_range_multiple_windows():
    chunks = split_date_range(
        date(2026, 1, 1),
        date(2026, 2, 5),
    )

    assert chunks == [
        (date(2026, 1, 1), date(2026, 1, 30)),
        (date(2026, 1, 31), date(2026, 2, 5)),
    ]


def test_split_date_range_has_no_overlap():
    chunks = split_date_range(
        date(2026, 1, 1),
        date(2026, 3, 15),
    )

    for previous, current in zip(chunks, chunks[1:]):
        assert previous[1] + timedelta(days=1) == current[0]


def test_split_date_range_rejects_invalid_dates():
    with pytest.raises(ValueError):
        split_date_range(
            date(2026, 2, 1),
            date(2026, 1, 1),
        )


def test_split_date_range_rejects_invalid_chunk_size():
    with pytest.raises(ValueError):
        split_date_range(
            date(2026, 1, 1),
            date(2026, 1, 5),
            max_days=0,
        )


def test_select_nearest_nifty_future():
    nearest = SimpleNamespace(
        instrument_id="NSE-FUT-NIFTY-20261126",
        symbol="NIFTY 26 NOV FUT",
        expiry_date=date(2026, 11, 26),
    )

    later = SimpleNamespace(
        instrument_id="NSE-FUT-NIFTY-20261231",
        symbol="NIFTY 31 DEC FUT",
        expiry_date=date(2026, 12, 31),
    )

    master = SimpleNamespace(
        get_futures_by_underlying=lambda **kwargs: [later, nearest]
    )

    result = select_nearest_nifty_future(
        master=master,
        as_of=date(2026, 11, 25),
    )

    assert result.instrument_id == "NSE-FUT-NIFTY-20261126"


def test_select_nearest_future_ignores_expired_contract():
    expired = SimpleNamespace(
        instrument_id="NSE-FUT-NIFTY-20261120",
        symbol="NIFTY 20 NOV FUT",
        expiry_date=date(2026, 11, 20),
    )

    active = SimpleNamespace(
        instrument_id="NSE-FUT-NIFTY-20261126",
        symbol="NIFTY 26 NOV FUT",
        expiry_date=date(2026, 11, 26),
    )

    master = SimpleNamespace(
        get_futures_by_underlying=lambda **kwargs: [expired, active]
    )

    result = select_nearest_nifty_future(
        master=master,
        as_of=date(2026, 11, 25),
    )

    assert result.instrument_id == active.instrument_id


def test_select_nearest_future_fails_when_none_available():
    master = SimpleNamespace(
        get_futures_by_underlying=lambda **kwargs: []
    )

    with pytest.raises(IngestionError):
        select_nearest_nifty_future(
            master=master,
            as_of=date(2026, 11, 25),
        )
