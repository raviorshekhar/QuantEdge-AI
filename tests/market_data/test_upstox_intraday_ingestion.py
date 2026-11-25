
from datetime import date, datetime, timezone
from types import SimpleNamespace

from quantedge.market_data.ingest_upstox import (
    fetch_candles_for_range,
)


class FakeClient:
    def __init__(self):
        self.historical_calls = []
        self.intraday_calls = []

    def fetch_instrument_candles(self, **kwargs):
        self.historical_calls.append(kwargs)
        return [
            SimpleNamespace(
                timestamp=datetime(2026, 11, 24, 9, 15, tzinfo=timezone.utc)
            )
        ]

    def fetch_instrument_intraday_candles(self, **kwargs):
        self.intraday_calls.append(kwargs)
        return [
            SimpleNamespace(
                timestamp=datetime(2026, 11, 25, 3, 45, tzinfo=timezone.utc)
            )
        ]


def test_fetch_combines_historical_and_intraday():
    client = FakeClient()

    result = fetch_candles_for_range(
        client=client,
        master=object(),
        instrument_id="NSE-FUT-NIFTY-20261229",
        as_of=date(2026, 11, 25),
        from_date=date(2026, 11, 24),
        to_date=date(2026, 11, 25),
    )

    assert len(client.historical_calls) == 1
    assert len(client.intraday_calls) == 1
    assert len(result) == 2
    assert result[0].timestamp < result[1].timestamp


def test_historical_only_for_completed_date_range():
    client = FakeClient()

    fetch_candles_for_range(
        client=client,
        master=object(),
        instrument_id="NSE-FUT-NIFTY-20261229",
        as_of=date(2026, 11, 25),
        from_date=date(2026, 11, 20),
        to_date=date(2026, 11, 24),
    )

    assert len(client.historical_calls) == 1
    assert len(client.intraday_calls) == 0

    call = client.historical_calls[0]
    assert call["from_date"] == date(2026, 11, 20)
    assert call["to_date"] == date(2026, 11, 24)


def test_intraday_only_for_current_date():
    client = FakeClient()

    fetch_candles_for_range(
        client=client,
        master=object(),
        instrument_id="NSE-FUT-NIFTY-20261229",
        as_of=date(2026, 11, 25),
        from_date=date(2026, 11, 25),
        to_date=date(2026, 11, 25),
    )

    assert len(client.historical_calls) == 0
    assert len(client.intraday_calls) == 1
