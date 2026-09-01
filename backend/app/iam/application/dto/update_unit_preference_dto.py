from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateUnitPreferenceDTO:
    preferred_unit_system: str