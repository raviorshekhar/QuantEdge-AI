
from datetime import date
from decimal import Decimal

import httpx
import pytest

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import Instrument, InstrumentType
from quantedge.instruments.provider_mapping import InstrumentProviderMapping
from quantedge.market_data.providers.upstox import (
    UpstoxHistoricalClient,
)


AS_OF = date(2026, 11, 25)
FROM_DATE = date(2026, 11, 20)
TO_DATE = date(2026, 11, 25)

INSTRUMENT_ID = "QE-FUT-001"
UPSTOX_KEY = "NSE_FO|12345"


def create_instrument_master(
    provider="UPSTOX",
    valid_from=date(2026, 1, 1),
    valid_to=None,
):
    master = InstrumentMaster()

    underlying = Instrument(
        instrument_id="QE-NIFTY-INDEX",
        exchange="NSE",
        instrument_type=InstrumentType.INDEX,
        symbol="NIFTY",
        name="NIFTY 50",
    )

    future = Instrument(
        instrument_id=INSTRUMENT_ID,
        exchange="NSE",
        instrument_type=InstrumentType.FUTURE,
        symbol="NIFTY-FUT",
        name="NIFTY Futures",
        underlying_id="QE-NIFTY-INDEX",
        expiry_date=date(2026, 11, 26),
        lot_size=1,
        tick_size=Decimal("0.05"),
    )

    master.register_instrument(underlying)
    master.register_instrument(future)

    mapping = InstrumentProviderMapping(
        mapping_id="MAP-001",
        instrument_id=INSTRUMENT_ID,
        provider=provider,
        provider_instrument_id=UPSTOX_KEY,
        provider_symbol="NIFTY FUT",
        exchange="NSE",
        segment="NSE_FO",
        valid_from=valid_from,
        valid_to=valid_to,
    )

    master.register_mapping(mapping)

    return master


def test_resolve_valid_upstox_mapping():
    master = create_instrument_master()

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id=INSTRUMENT_ID,
        as_of=AS_OF,
    )

    assert mapping is not None
    assert mapping.provider == "UPSTOX"
    assert mapping.provider_instrument_id == UPSTOX_KEY


def test_unknown_instrument_returns_no_mapping():
    master = create_instrument_master()

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id="QE-UNKNOWN-001",
        as_of=AS_OF,
    )

    assert mapping is None


def test_missing_provider_mapping_returns_none():
    master = InstrumentMaster()

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id=INSTRUMENT_ID,
        as_of=AS_OF,
    )

    assert mapping is None


def test_expired_provider_mapping_returns_none():
    master = create_instrument_master(
        valid_to=date(2026, 11, 20),
    )

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id=INSTRUMENT_ID,
        as_of=AS_OF,
    )

    assert mapping is None


def test_wrong_provider_returns_no_mapping():
    master = create_instrument_master(
        provider="ZERODHA",
    )

    mapping = master.get_provider_mapping(
        provider="UPSTOX",
        instrument_id=INSTRUMENT_ID,
        as_of=AS_OF,
    )

    assert mapping is None


def test_fetch_instrument_candles_uses_provider_mapping():
    master = create_instrument_master()

    requested_urls = []

    def handler(request):
        requested_urls.append(request.url)

        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "candles": [
                        [
                            "2026-11-25T09:15:00+05:30",
                            25100,
                            25115,
                            25095,
                            25110,
                            12500,
                            185000,
                        ]
                    ]
                },
            },
        )

    mock_client = httpx.Client(
        transport=httpx.MockTransport(handler)
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        candles = client.fetch_instrument_candles(
            instrument_master=master,
            instrument_id=INSTRUMENT_ID,
            as_of=AS_OF,
            from_date=FROM_DATE,
            to_date=TO_DATE,
        )

    mock_client.close()

    assert len(requested_urls) == 1
    assert UPSTOX_KEY in requested_urls[0].path
    assert len(candles) == 1
    assert candles[0].instrument_id == INSTRUMENT_ID
    assert candles[0].open_interest == 185000


def test_fetch_instrument_candles_rejects_missing_mapping():
    master = InstrumentMaster()

    mock_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        )
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(
            ValueError,
            match="No active Upstox mapping",
        ):
            client.fetch_instrument_candles(
                instrument_master=master,
                instrument_id=INSTRUMENT_ID,
                as_of=AS_OF,
                from_date=FROM_DATE,
                to_date=TO_DATE,
            )

    mock_client.close()


def test_fetch_instrument_candles_rejects_expired_mapping():
    master = create_instrument_master(
        valid_to=date(2026, 11, 20),
    )

    mock_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        )
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(
            ValueError,
            match="No active Upstox mapping",
        ):
            client.fetch_instrument_candles(
                instrument_master=master,
                instrument_id=INSTRUMENT_ID,
                as_of=AS_OF,
                from_date=FROM_DATE,
                to_date=TO_DATE,
            )

    mock_client.close()


def test_fetch_instrument_candles_rejects_wrong_provider():
    master = create_instrument_master(
        provider="ZERODHA",
    )

    mock_client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        )
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(
            ValueError,
            match="No active Upstox mapping",
        ):
            client.fetch_instrument_candles(
                instrument_master=master,
                instrument_id=INSTRUMENT_ID,
                as_of=AS_OF,
                from_date=FROM_DATE,
                to_date=TO_DATE,
            )

    mock_client.close()
