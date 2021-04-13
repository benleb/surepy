from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from surepy.enums import EntityType, Location


class SurepyEntity(ABC):
    def __init__(self, data: Dict[str, Any]):

        # sure petcare id
        self._id: int = int(data.get("id", data.get("_id")))

        # self._sac: SureAPIClient = sac
        self._data = data
        self._type = EntityType(int(data.get("product_id", 0)))

        self._name: str = str(self._data.get("name"))

    @property
    def id(self) -> int:
        return self._id

    @property
    def unique_id(self):
        return f"{self.household_id}-{self.id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def full_name(self) -> str:
        return f"{self.type.name}_{self.name}"

    @property
    def type(self) -> EntityType:
        return self._type

    @property
    def household_id(self) -> Optional[int]:
        """ID of the household the entity belongs to."""
        return (
            int(household_id) if (household_id := self._data.get("household_id")) else None  # noqa
        )


@dataclass
class StateFeeding:
    change: List[float]
    at: Optional[datetime]


@dataclass
class StateDrinking:
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
