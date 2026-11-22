
from quantedge.instruments.models import Instrument, InstrumentType
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
            same_instrument = existing.instrument_id == mapping.instrument_id

            if same_provider and same_instrument:
                if self._mappings_overlap(existing, mapping):
                    raise ValueError(
                        "Provider mapping validity periods cannot overlap "
                        "for the same provider and instrument"
                    )

        self._mappings[mapping.mapping_id] = mapping

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def get_mapping(self, mapping_id: str) -> InstrumentProviderMapping | None:
        return self._mappings.get(mapping_id)
