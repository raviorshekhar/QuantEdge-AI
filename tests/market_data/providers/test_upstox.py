import httpx
from datetime import date
from quantedge.market_data.providers.upstox import (
    UpstoxAPIError,
    UpstoxHistoricalClient,
    UpstoxResponseError,
    create_upstox_client,
    map_upstox_candles,
)
from quantedge.market_data.providers.upstox import (
    UpstoxAPIError,
    UpstoxHistoricalClient,
)
from datetime import timezone
from decimal import Decimal

import pytest

from quantedge.market_data.providers.upstox import (
    UpstoxResponseError,
    map_upstox_candles,
)


@pytest.fixture
def valid_upstox_response():
    return {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:16:00+05:30",
                    25110,
                    25120,
                    25105,
                    25115,
                    11800,
                    185250,
                ],
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25115,
                    25095,
                    25110,
                    12500,
                    185000,
                ],
            ]
        },
    }


def test_map_valid_upstox_candles(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert len(candles) == 2
    assert candles[0].instrument_id == "QE-FUT-001"
    assert candles[0].open == Decimal("25100")
    assert candles[0].close == Decimal("25110")
    assert candles[0].volume == 12500
    assert candles[0].open_interest == 185000


def test_candles_are_sorted_chronologically(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].timestamp < candles[1].timestamp


def test_timestamp_is_normalized_to_utc(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].timestamp.tzinfo == timezone.utc


def test_missing_open_interest_is_none():
    response = {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25115,
                    25095,
                    25110,
                    12500,
                    None,
                ]
            ]
        },
    }

    candles = map_upstox_candles(
        response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].open_interest is None


def test_empty_candle_response_returns_empty_list():
    response = {
        "status": "success",
        "data": {"candles": []},
    }

    candles = map_upstox_candles(
        response,
        instrument_id="QE-FUT-001",
    )

    assert candles == []


def test_unsuccessful_response_raises_error():
    response = {
        "status": "error",
        "data": {},
    }

    with pytest.raises(UpstoxResponseError, match="unsuccessful"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_missing_candle_collection_raises_error():
    response = {
        "status": "success",
        "data": {},
    }

    with pytest.raises(UpstoxResponseError, match="candle collection"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_invalid_candle_structure_raises_error():
    response = {
        "status": "success",
        "data": {
            "candles": [
                ["2026-11-18T09:15:00+05:30", 25100, 25115]
            ]
        },
    }

    with pytest.raises(UpstoxResponseError, match="candle structure"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_invalid_ohlc_data_raises_error():
    response = {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25000,
                    25095,
                    25110,
                    12500,
                    185000,
                ]
            ]
        },
    }

    with pytest.raises(UpstoxResponseError, match="Unable to map"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def make_mock_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_historical_client_successful_request():
    def handler(request):
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path.endswith(
            "/NSE_FO%7C12345/minutes/1/2026-11-25/2026-11-20"
        )

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

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        candles = client.fetch_historical_candles(
            instrument_key="NSE_FO|12345",
            instrument_id="QE-FUT-001",
            from_date=date(2026, 11, 20),
            to_date=date(2026, 11, 25),
        )

    assert len(candles) == 1
    assert candles[0].open_interest == 185000
    assert candles[0].instrument_id == "QE-FUT-001"

    mock_client.close()


def test_historical_client_http_error():
    def handler(request):
        return httpx.Response(401, json={"message": "Unauthorized"})

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="invalid-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="HTTP error: 401"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_connection_error():
    def handler(request):
        raise httpx.ConnectError("Connection failed")

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="Unable to connect"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_invalid_json():
    def handler(request):
        return httpx.Response(
            200,
            content=b"not-valid-json",
        )

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="invalid JSON"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_invalid_api_response():
    def handler(request):
        return httpx.Response(
            200,
            json={"status": "success", "data": {}},
        )

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="Unable to process"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_rejects_invalid_date_range():
    mock_client = make_mock_client(
        lambda request: httpx.Response(200, json={})
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(ValueError, match="from_date"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 25),
                to_date=date(2026, 11, 20),
            )

    mock_client.close()


from datetime import date, timezone
from decimal import Decimal

import httpx
import pytest

from quantedge.market_data.providers.upstox import (
    UpstoxAPIError,
    UpstoxHistoricalClient,
    UpstoxResponseError,
    map_upstox_candles,
)


@pytest.fixture
def valid_upstox_response():
    return {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:16:00+05:30",
                    25110,
                    25120,
                    25105,
                    25115,
                    11800,
                    185250,
                ],
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25115,
                    25095,
                    25110,
                    12500,
                    185000,
                ],
            ]
        },
    }


# ---------------------------------------------------------
# Response Mapper Tests
# ---------------------------------------------------------

def test_map_valid_upstox_candles(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert len(candles) == 2
    assert candles[0].instrument_id == "QE-FUT-001"
    assert candles[0].open == Decimal("25100")
    assert candles[0].close == Decimal("25110")
    assert candles[0].volume == 12500
    assert candles[0].open_interest == 185000


def test_candles_are_sorted_chronologically(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].timestamp < candles[1].timestamp


def test_timestamp_is_normalized_to_utc(valid_upstox_response):
    candles = map_upstox_candles(
        valid_upstox_response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].timestamp.tzinfo == timezone.utc


def test_missing_open_interest_is_none():
    response = {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25115,
                    25095,
                    25110,
                    12500,
                    None,
                ]
            ]
        },
    }

    candles = map_upstox_candles(
        response,
        instrument_id="QE-FUT-001",
    )

    assert candles[0].open_interest is None


def test_empty_candle_response_returns_empty_list():
    response = {
        "status": "success",
        "data": {"candles": []},
    }

    candles = map_upstox_candles(
        response,
        instrument_id="QE-FUT-001",
    )

    assert candles == []


def test_unsuccessful_response_raises_error():
    response = {
        "status": "error",
        "data": {},
    }

    with pytest.raises(UpstoxResponseError, match="unsuccessful"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_missing_candle_collection_raises_error():
    response = {
        "status": "success",
        "data": {},
    }

    with pytest.raises(UpstoxResponseError, match="candle collection"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_invalid_candle_structure_raises_error():
    response = {
        "status": "success",
        "data": {
            "candles": [
                ["2026-11-18T09:15:00+05:30", 25100, 25115]
            ]
        },
    }

    with pytest.raises(UpstoxResponseError, match="candle structure"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


def test_invalid_ohlc_data_raises_error():
    response = {
        "status": "success",
        "data": {
            "candles": [
                [
                    "2026-11-18T09:15:00+05:30",
                    25100,
                    25000,
                    25095,
                    25110,
                    12500,
                    185000,
                ]
            ]
        },
    }

    with pytest.raises(UpstoxResponseError, match="Unable to map"):
        map_upstox_candles(
            response,
            instrument_id="QE-FUT-001",
        )


# ---------------------------------------------------------
# HTTP Client Tests
# ---------------------------------------------------------

def make_mock_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_historical_client_successful_request():
    def handler(request):
        assert request.method == "GET"
        assert request.headers["Authorization"] == "Bearer test-token"

        # httpx decodes the URL path, so the pipe is literal here.
        assert request.url.path.endswith(
            "/NSE_FO|12345/minutes/1/2026-11-25/2026-11-20"
        )

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

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        candles = client.fetch_historical_candles(
            instrument_key="NSE_FO|12345",
            instrument_id="QE-FUT-001",
            from_date=date(2026, 11, 20),
            to_date=date(2026, 11, 25),
        )

    assert len(candles) == 1
    assert candles[0].open_interest == 185000
    assert candles[0].instrument_id == "QE-FUT-001"

    mock_client.close()


def test_historical_client_http_error():
    def handler(request):
        return httpx.Response(
            401,
            json={"message": "Unauthorized"},
        )

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="invalid-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="HTTP error: 401"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_connection_error():
    def handler(request):
        raise httpx.ConnectError("Connection failed")

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="Unable to connect"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_invalid_json():
    def handler(request):
        return httpx.Response(
            200,
            content=b"not-valid-json",
        )

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="invalid JSON"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_invalid_api_response():
    def handler(request):
        return httpx.Response(
            200,
            json={"status": "success", "data": {}},
        )

    mock_client = make_mock_client(handler)

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(UpstoxAPIError, match="Unable to process"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 20),
                to_date=date(2026, 11, 25),
            )

    mock_client.close()


def test_historical_client_rejects_invalid_date_range():
    mock_client = make_mock_client(
        lambda request: httpx.Response(200, json={})
    )

    with UpstoxHistoricalClient(
        access_token="test-token",
        http_client=mock_client,
    ) as client:
        with pytest.raises(ValueError, match="from_date"):
            client.fetch_historical_candles(
                instrument_key="NSE_FO|12345",
                instrument_id="QE-FUT-001",
                from_date=date(2026, 11, 25),
                to_date=date(2026, 11, 20),
            )

    mock_client.close()


from quantedge.shared.config import Settings


def test_create_upstox_client_with_settings():
    settings = Settings(
        upstox_access_token="test-secret-token"
    )

    client = create_upstox_client(settings)

    assert isinstance(client, UpstoxHistoricalClient)
    assert client._access_token == "test-secret-token"


def test_create_upstox_client_without_token_raises_error():
    settings = Settings(
        upstox_access_token=None
    )

    with pytest.raises(
        ValueError,
        match="UPSTOX_ACCESS_TOKEN is not configured",
    ):
        create_upstox_client(settings)


def test_upstox_access_token_is_secret():
    settings = Settings(
        upstox_access_token="test-secret-token"
    )

    assert "test-secret-token" not in str(
        settings.model_dump()
    )