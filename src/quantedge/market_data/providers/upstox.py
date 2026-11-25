
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from quantedge.instruments.master import InstrumentMaster
from quantedge.market_data.models import MarketCandle
from quantedge.shared.config import Settings, get_settings


class UpstoxResponseError(ValueError):
    """Raised when an Upstox response cannot be mapped."""


class UpstoxAPIError(RuntimeError):
    """Raised when an Upstox API request fails."""


def map_upstox_candles(
    response: dict[str, Any],
    instrument_id: str,
    timeframe: str = "1m",
) -> list[MarketCandle]:
    """
    Convert Upstox Historical Candle V3 response
    into provider-independent MarketCandle objects.

    Upstox candle structure:
    [timestamp, open, high, low, close, volume, open_interest]
    """

    if response.get("status") != "success":
        raise UpstoxResponseError(
            "Upstox API returned an unsuccessful response"
        )

    data = response.get("data")

    if not isinstance(data, dict):
        raise UpstoxResponseError(
            "Invalid Upstox response data"
        )

    raw_candles = data.get("candles")

    if not isinstance(raw_candles, list):
        raise UpstoxResponseError(
            "Invalid or missing candle collection"
        )

    candles: list[MarketCandle] = []

    for index, raw in enumerate(raw_candles):
        if not isinstance(raw, (list, tuple)) or len(raw) != 7:
            raise UpstoxResponseError(
                f"Invalid candle structure at index {index}"
            )

        try:
            timestamp = datetime.fromisoformat(raw[0])

            open_price = Decimal(str(raw[1]))
            high_price = Decimal(str(raw[2]))
            low_price = Decimal(str(raw[3]))
            close_price = Decimal(str(raw[4]))

            volume = int(raw[5]) if raw[5] is not None else None
            open_interest = (
                int(raw[6]) if raw[6] is not None else None
            )

            candle = MarketCandle(
                instrument_id=instrument_id,
                timestamp=timestamp,
                timeframe=timeframe,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                open_interest=open_interest,
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
            ValidationError,
        ) as exc:
            raise UpstoxResponseError(
                f"Unable to map Upstox candle at index {index}: {exc}"
            ) from exc

        candles.append(candle)

    return sorted(
        candles,
        key=lambda candle: candle.timestamp,
    )


class UpstoxHistoricalClient:
    BASE_URL = "https://api.upstox.com"

    def __init__(
        self,
        access_token: str,
        timeout: float = 15.0,
        http_client: httpx.Client | None = None,
    ):
        if not access_token:
            raise ValueError("Upstox access token is required")

        self._access_token = access_token
        self._timeout = timeout
        self._http_client = http_client
        self._owns_client = http_client is None

    def __enter__(self):
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=self._timeout
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def fetch_instrument_candles(
        self,
        instrument_master: InstrumentMaster,
        instrument_id: str,
        as_of: date,
        from_date: date,
        to_date: date,
    ) -> list[MarketCandle]:

        mapping = instrument_master.get_provider_mapping(
            provider="UPSTOX",
            instrument_id=instrument_id,
            as_of=as_of,
        )

        if mapping is None:
            raise ValueError(
                f"No active Upstox mapping found for {instrument_id}"
            )

        return self.fetch_historical_candles(
            instrument_key=mapping.provider_instrument_id,
            instrument_id=instrument_id,
            from_date=from_date,
            to_date=to_date,
        )

    def fetch_historical_candles(
        self,
        instrument_key: str,
        instrument_id: str,
        from_date: date,
        to_date: date,
    ) -> list[MarketCandle]:

        if not instrument_key:
            raise ValueError("Instrument key is required")

        if from_date > to_date:
            raise ValueError("from_date cannot be after to_date")

        if self._http_client is None:
            raise RuntimeError(
                "Use UpstoxHistoricalClient as a context manager"
            )

        encoded_key = quote(instrument_key, safe="")

        url = (
            f"{self.BASE_URL}/v3/historical-candle/"
            f"{encoded_key}/minutes/1/"
            f"{to_date.isoformat()}/{from_date.isoformat()}"
        )

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            response = self._http_client.get(
                url,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPStatusError as exc:
            raise UpstoxAPIError(
                f"Upstox HTTP error: {exc.response.status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise UpstoxAPIError(
                f"Unable to connect to Upstox: {exc}"
            ) from exc

        except ValueError as exc:
            raise UpstoxAPIError(
                "Upstox returned invalid JSON"
            ) from exc

        try:
            return map_upstox_candles(
                response=payload,
                instrument_id=instrument_id,
                timeframe="1m",
            )
        except UpstoxResponseError as exc:
            raise UpstoxAPIError(
                f"Unable to process Upstox response: {exc}"
            ) from exc

    def fetch_instrument_intraday_candles(
        self,
        instrument_master: InstrumentMaster,
        instrument_id: str,
        as_of: date,
    ) -> list[MarketCandle]:
        """Fetch current-day candles using the provider mapping."""

        mapping = instrument_master.get_provider_mapping(
            provider="UPSTOX",
            instrument_id=instrument_id,
            as_of=as_of,
        )

        if mapping is None:
            raise ValueError(
                f"No active Upstox mapping found for {instrument_id}"
            )

        return self.fetch_intraday_candles(
            instrument_key=mapping.provider_instrument_id,
            instrument_id=instrument_id,
        )

    def fetch_intraday_candles(
        self,
        instrument_key: str,
        instrument_id: str,
    ) -> list[MarketCandle]:
        """Fetch current-day 1-minute candles from Upstox."""

        if not instrument_key:
            raise ValueError("Instrument key is required")

        if self._http_client is None:
            raise RuntimeError(
                "Use UpstoxHistoricalClient as a context manager"
            )

        encoded_key = quote(instrument_key, safe="")

        url = (
            f"{self.BASE_URL}/v3/historical-candle/intraday/"
            f"{encoded_key}/minutes/1"
        )

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
        }

        try:
            response = self._http_client.get(
                url,
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPStatusError as exc:
            raise UpstoxAPIError(
                f"Upstox intraday HTTP error: {exc.response.status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise UpstoxAPIError(
                f"Unable to connect to Upstox intraday API: {exc}"
            ) from exc

        except ValueError as exc:
            raise UpstoxAPIError(
                "Upstox intraday API returned invalid JSON"
            ) from exc

        try:
            return map_upstox_candles(
                response=payload,
                instrument_id=instrument_id,
                timeframe="1m",
            )

        except UpstoxResponseError as exc:
            raise UpstoxAPIError(
                f"Unable to process Upstox intraday response: {exc}"
            ) from exc


def create_upstox_client(
    settings: Settings | None = None,
) -> UpstoxHistoricalClient:
    """
    Create an Upstox client using application settings.

    The access token is stored as SecretStr and is
    revealed only when passed to the HTTP client.
    """

    app_settings = settings or get_settings()

    access_token = app_settings.upstox_access_token

    if access_token is None:
        raise ValueError(
            "UPSTOX_ACCESS_TOKEN is not configured"
        )

    return UpstoxHistoricalClient(
        access_token=access_token.get_secret_value()
    )
