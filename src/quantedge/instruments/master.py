
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
            if instrument.underlying_id not in self._instruments:
                raise ValueError("Underlying instrument does not exist")

        self._instruments[instrument.instrument_id] = instrument

    def register_mapping(self, mapping: InstrumentProviderMapping) -> None:

        if mapping.mapping_id in self._mappings:
            raise ValueError("Mapping ID already exists")

        if mapping.instrument_id not in self._instruments:
            raise ValueError("Referenced instrument does not exist")

        self._mappings[mapping.mapping_id] = mapping

    def get_instrument(self, instrument_id: str) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def get_mapping(self, mapping_id: str) -> InstrumentProviderMapping | None:
        return self._mappings.get(mapping_id)
