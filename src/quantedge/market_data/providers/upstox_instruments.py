
import gzip
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from quantedge.instruments.master import InstrumentMaster
from quantedge.instruments.models import Instrument, InstrumentStatus, InstrumentType
from quantedge.instruments.provider_mapping import InstrumentProviderMapping


class UpstoxInstrumentError(ValueError):
    """Raised when Upstox instrument master data is invalid."""


class UpstoxInstrumentMasterLoader:
    NSE_INSTRUMENTS_URL = (
        "https://assets.upstox.com/market-quote/"
        "instruments/exchange/NSE.json.gz"
    )

    PROVIDER = "UPSTOX"
    EXCHANGE = "NSE"
    IST = ZoneInfo("Asia/Kolkata")

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def download(self) -> list[dict[str, Any]]:
        """Download and decompress Upstox NSE BOD instrument JSON."""

        try:
            response = httpx.get(
                self.NSE_INSTRUMENTS_URL,
                timeout=self.timeout,
            )
            response.raise_for_status()

            content = gzip.decompress(response.content)
            records = json.loads(content)

        except httpx.HTTPError as exc:
            raise UpstoxInstrumentError(
                f"Unable to download Upstox instruments: {exc}"
            ) from exc
        except (OSError, gzip.BadGzipFile, json.JSONDecodeError) as exc:
            raise UpstoxInstrumentError(
                f"Unable to decode Upstox instrument file: {exc}"
            ) from exc

        if not isinstance(records, list):
            raise UpstoxInstrumentError(
                "Upstox instrument master must contain a JSON array"
            )

        return records

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", value.upper())

    @classmethod
    def _is_nifty50_index(cls, record: dict[str, Any]) -> bool:
        return (
            record.get("segment") == "NSE_INDEX"
            and record.get("instrument_type") == "INDEX"
            and (
                cls._normalize(record.get("trading_symbol", "")) == "NIFTY50"
                or cls._normalize(record.get("name", "")) == "NIFTY50"
            )
        )

    @staticmethod
    def _expiry_date(value: Any) -> date:
        """Convert Upstox expiry epoch milliseconds to exchange-local date."""

        try:
            expiry_timestamp = int(value)

            expiry = datetime.fromtimestamp(
                expiry_timestamp / 1000,
                tz=ZoneInfo("Asia/Kolkata"),
            )

            return expiry.date()

        except (TypeError, ValueError, OSError, OverflowError) as exc:
            raise UpstoxInstrumentError(
                f"Invalid futures expiry: {value}"
            ) from exc

    @staticmethod
    def _decimal(value: Any, field: str) -> Decimal:
        try:
            result = Decimal(str(value))
            if not result.is_finite() or result <= 0:
                raise ValueError
            return result
        except (InvalidOperation, TypeError, ValueError):
            raise UpstoxInstrumentError(
                f"Invalid {field}: {value}"
            )

    def build_instruments(
        self,
        records: list[dict[str, Any]],
        as_of: date,
    ) -> tuple[list[Instrument], list[InstrumentProviderMapping]]:
        """
        Build QuantEdge NIFTY 50 index and NIFTY futures
        instruments from Upstox NSE instrument records.
        """

        if not isinstance(records, list):
            raise UpstoxInstrumentError(
                "Instrument records must be a list"
            )

        indexes = [
            record
            for record in records
            if isinstance(record, dict)
            and self._is_nifty50_index(record)
        ]

        if len(indexes) != 1:
            raise UpstoxInstrumentError(
                f"Expected exactly one NIFTY 50 index, found {len(indexes)}"
            )

        index_record = indexes[0]

        index_key = index_record.get("instrument_key")
        index_symbol = index_record.get("trading_symbol")
        index_name = index_record.get("name")

        if not all(
            isinstance(value, str) and value.strip()
            for value in (index_key, index_symbol, index_name)
        ):
            raise UpstoxInstrumentError(
                "NIFTY 50 index record has incomplete identifiers"
            )

        index_id = "NSE-INDEX-NIFTY50"

        instruments = [
            Instrument(
                instrument_id=index_id,
                exchange=self.EXCHANGE,
                instrument_type=InstrumentType.INDEX,
                symbol=index_symbol,
                name=index_name,
                status=InstrumentStatus.ACTIVE,
            )
        ]

        mappings = [
            InstrumentProviderMapping(
                mapping_id="UPSTOX-NSE-INDEX-NIFTY50",
                instrument_id=index_id,
                provider=self.PROVIDER,
                provider_instrument_id=index_key,
                provider_symbol=index_symbol,
                exchange=self.EXCHANGE,
                segment="NSE_INDEX",
                valid_from=as_of,
            )
        ]

        futures = [
            record
            for record in records
            if isinstance(record, dict)
            and record.get("segment") == "NSE_FO"
            and record.get("instrument_type") == "FUT"
            and record.get("underlying_symbol", "").upper() == "NIFTY"
            and record.get("underlying_type") == "INDEX"
            and record.get("underlying_key") == index_key
        ]

        if not futures:
            raise UpstoxInstrumentError(
                "No NIFTY 50 futures contracts found"
            )

        seen_keys: set[str] = set()
        seen_expiries: set[date] = set()

        for record in futures:
            instrument_key = record.get("instrument_key")
            trading_symbol = record.get("trading_symbol")
            name = record.get("name")

            if not all(
                isinstance(value, str) and value.strip()
                for value in (instrument_key, trading_symbol, name)
            ):
                raise UpstoxInstrumentError(
                    "NIFTY futures record has incomplete identifiers"
                )

            if instrument_key in seen_keys:
                raise UpstoxInstrumentError(
                    f"Duplicate Upstox instrument key: {instrument_key}"
                )

            expiry = self._expiry_date(record.get("expiry"))

            if expiry in seen_expiries:
                raise UpstoxInstrumentError(
                    f"Duplicate NIFTY futures expiry: {expiry}"
                )

            seen_keys.add(instrument_key)
            seen_expiries.add(expiry)

            lot_size = record.get("lot_size")

            if (
                isinstance(lot_size, bool)
                or not isinstance(lot_size, int)
                or lot_size <= 0
            ):
                raise UpstoxInstrumentError(
                    f"Invalid futures lot size: {lot_size}"
                )

            tick_size = self._decimal(
                record.get("tick_size"),
                "tick_size",
            )

            instrument_id = f"NSE-FUT-NIFTY-{expiry:%Y%m%d}"

            status = (
                InstrumentStatus.ACTIVE
                if expiry >= as_of
                else InstrumentStatus.EXPIRED
            )

            instruments.append(
                Instrument(
                    instrument_id=instrument_id,
                    exchange=self.EXCHANGE,
                    instrument_type=InstrumentType.FUTURE,
                    symbol=trading_symbol,
                    name=name,
                    underlying_id=index_id,
                    expiry_date=expiry,
                    lot_size=lot_size,
                    tick_size=tick_size,
                    status=status,
                )
            )

            mappings.append(
                InstrumentProviderMapping(
                    mapping_id=f"UPSTOX-{instrument_id}",
                    instrument_id=instrument_id,
                    provider=self.PROVIDER,
                    provider_instrument_id=instrument_key,
                    provider_symbol=trading_symbol,
                    exchange=self.EXCHANGE,
                    segment="NSE_FO",
                    valid_from=as_of,
                )
            )

        return instruments, mappings

    def register_into(
        self,
        records: list[dict[str, Any]],
        master: InstrumentMaster,
        as_of: date,
    ) -> int:
        """Register validated instruments and mappings into InstrumentMaster."""

        instruments, mappings = self.build_instruments(
            records=records,
            as_of=as_of,
        )

        # Register underlying index before futures.
        for instrument in instruments:
            master.register_instrument(instrument)

        for mapping in mappings:
            master.register_mapping(mapping)

        return len(instruments)

    def download_and_register(
        self,
        master: InstrumentMaster,
        as_of: date,
    ) -> int:
        records = self.download()

        return self.register_into(
            records=records,
            master=master,
            as_of=as_of,
        )
