from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from surepy.client import SureAPIClient
from surepy.enums import EntityType, Location


class SurepyEntity(ABC):
    def __init__(self, data: Dict[str, Any], entity_type: EntityType, sac: SureAPIClient):

        # sure petcare id
        self._id: int = int(data["id"])

        self._sac: SureAPIClient = sac
        self._data = data
        self._type = entity_type

        self._name: str = str(self._data.get("name"))

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> EntityType:
        return self._type

    @property
    def household_id(self) -> Optional[int]:
        """ID of the household the entity belongs to."""
        return int(household_id) if (household_id := self._data.get("household_id")) else None


class SurepyDevice(SurepyEntity, ABC):
    @property
    def serial(self) -> Optional[str]:
        """ID of the household the pet belongs to."""
        return str(serial) if (serial := self._data.get("serial_number")) else None


@dataclass
class StateFeeding:

    change: List[float]
    at: Optional[datetime]


@dataclass
class PetLocationData:

    where: Location
    since: Optional[datetime]

    def __str__(self) -> str:
        return self.where.name.title()


@dataclass
class PetActivity(PetLocationData):
    pass


@dataclass
class PetLocation(PetLocationData):
    pass
