
from datetime import date

from quantedge.instruments.models import (
    Instrument,
    InstrumentStatus,
    InstrumentType,
)
from quantedge.instruments.provider_mapping import InstrumentProviderMapping


class InstrumentMaster:

    def __init__(self):
        self._instruments: dict[str, Instrument] = {}
        self._mappings: dict[str, InstrumentProviderMapping] = {}

    def register_instrument(self, instrument: Instrument) -> None:

        if instrument.instrument_id in self._instruments:
            raise ValueError("Instrument ID already exists")

        if instrument.instrument_type == InstrumentType.FUTURE:

            underlying = self._instruments.get(instrument.underlying_id)

            if underlying is None:
                raise ValueError("Underlying instrument does not exist")

            if underlying.instrument_type != InstrumentType.INDEX:
                raise ValueError("Future underlying must be an INDEX")

            if underlying.exchange != instrument.exchange:
                raise ValueError(
                    "Future and underlying must belong to the same exchange"
                )

        self._instruments[instrument.instrument_id] = instrument

    @staticmethod
    def _mappings_overlap(
        existing: InstrumentProviderMapping,
        new: InstrumentProviderMapping,
    ) -> bool:

        existing_end = existing.valid_to
        new_end = new.valid_to

        existing_starts_before_new_ends = (
            new_end is None or existing.valid_from <= new_end
        )

        new_starts_before_existing_ends = (
            existing_end is None or new.valid_from <= existing_end
        )

        return (
            existing_starts_before_new_ends
            and new_starts_before_existing_ends
        )

    def register_mapping(self, mapping: InstrumentProviderMapping) -> None:

        if mapping.mapping_id in self._mappings:
            raise ValueError("Mapping ID already exists")

        if mapping.instrument_id not in self._instruments:
            raise ValueError("Referenced instrument does not exist")

        for existing in self._mappings.values():

            same_provider = existing.provider == mapping.provider

            same_instrument = (
                existing.instrument_id == mapping.instrument_id
            )

            same_provider_instrument_id = (
                existing.provider_instrument_id
                == mapping.provider_instrument_id
            )

            if same_provider and same_instrument:
                if self._mappings_overlap(existing, mapping):
                    raise ValueError(
                        "Provider mapping validity periods cannot overlap "
                        "for the same provider and instrument"
                    )

            if same_provider and same_provider_instrument_id:
                if self._mappings_overlap(existing, mapping):
                    raise ValueError(
                        "Provider instrument ID validity periods cannot "
                        "overlap for the same provider"
                    )

        self._mappings[mapping.mapping_id] = mapping

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def get_mapping(self, mapping_id: str) -> InstrumentProviderMapping | None:
        return self._mappings.get(mapping_id)

    def resolve_provider_instrument(
        self,
        provider: str,
        provider_instrument_id: str,
        as_of: date,
    ) -> Instrument | None:

        matching_mappings = [
            mapping
            for mapping in self._mappings.values()
            if (
                mapping.provider == provider
                and mapping.provider_instrument_id == provider_instrument_id
                and mapping.valid_from <= as_of
                and (
                    mapping.valid_to is None
                    or as_of <= mapping.valid_to
                )
            )
        ]

        if not matching_mappings:
            return None

        if len(matching_mappings) > 1:
            raise ValueError(
                "Multiple provider mappings found for the supplied lookup"
            )

        return self._instruments.get(
            matching_mappings[0].instrument_id
        )

    def get_futures_by_underlying(
        self,
        underlying_id: str,
        status: InstrumentStatus | None = None,
        expiry_from: date | None = None,
        expiry_to: date | None = None,
        as_of: date | None = None,
    ) -> list[Instrument]:

        if (
            expiry_from is not None
            and expiry_to is not None
            and expiry_to < expiry_from
        ):
            raise ValueError(
                "expiry_to cannot be earlier than expiry_from"
            )

        effective_expiry_from = expiry_from

        if as_of is not None:
            if (
                effective_expiry_from is None
                or as_of > effective_expiry_from
            ):
                effective_expiry_from = as_of

        futures = [
            instrument
            for instrument in self._instruments.values()
            if (
                instrument.instrument_type == InstrumentType.FUTURE
                and instrument.underlying_id == underlying_id
                and (
                    status is None
                    or instrument.status == status
                )
                and (
                    effective_expiry_from is None
                    or instrument.expiry_date >= effective_expiry_from
                )
                and (
                    expiry_to is None
                    or instrument.expiry_date <= expiry_to
                )
            )
        ]

        return sorted(
            futures,
            key=lambda instrument: (
                instrument.expiry_date,
                instrument.instrument_id,
            ),
        )


    def get_provider_mapping(
        self,
        provider: str,
        instrument_id: str,
        as_of: date,
    ) -> InstrumentProviderMapping | None:

        matching_mappings = [
            mapping
            for mapping in self._mappings.values()
            if (
                mapping.provider == provider
                and mapping.instrument_id == instrument_id
                and mapping.valid_from <= as_of
                and (
                    mapping.valid_to is None
                    or as_of <= mapping.valid_to
                )
            )
        ]

        if not matching_mappings:
            return None

        if len(matching_mappings) > 1:
            raise ValueError(
                "Multiple provider mappings found for the supplied instrument"
            )

        return matching_mappings[0]
