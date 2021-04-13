"""
surepy.pet
====================================
The `Pet` class of surepy

|license-info|
"""


from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from surepy.entities import (
    PetActivity,
    PetLocation,
    StateDrinking,
    StateFeeding,
    SurepyEntity,
)
from surepy.entities.states import PetState
from surepy.enums import EntityType, FoodType, Location


class Pet(SurepyEntity):
    def __init__(self, data: Dict[str, Any]):

        super().__init__(data=data)

        self.pet_id: int = int(data["id"])

        self._type: EntityType = EntityType.PET
        self._data: Dict[str, Any] = data

        self._name = str(name) if (name := self._data.get("name")) else "Unnamed"

        self.state = PetState(data["status"])

    @property
    def id(self) -> int:
        """ID of the household the pet belongs to."""
        return self.pet_id

    @property
    def tag_id(self) -> Optional[int]:
        """ID of the household the pet belongs to."""
        return int(tag_id) if (tag_id := self._data.get("tag_id")) else None

    @property
    def food_type(self) -> Optional[str]:
        """Type of food."""
        return str(FoodType(type_id)) if (type_id := self._data.get("food_type_id")) else None

    @property
    def updated_at(self) -> Optional[datetime]:
        """Type of food."""
        return (
            datetime.fromisoformat(updated_at)
            if (updated_at := self._data.get("updated_at"))
            else None
        )

    @property
    def photo_url(self) -> Optional[str]:
        """Picture of the Pet."""
        return (
            urlparse(photo_url).geturl()
            if (photo_url := self._data.get("photo", {}).get("location"))
            else None
        )

    @property
    def at_home(self) -> bool:
        """Location of the Pet."""
        return bool(self.location.where == Location.INSIDE)

    @property
    def location(self) -> PetLocation:
        """Location of the Pet."""
        position = self._data.get("position", {})
        return PetLocation(
            where=Location(position.get("where", Location.UNKNOWN.value)),
            since=position.get("since", None),
        )

    @property
    def activity(self) -> PetActivity:
        """Last Activity of the Pet."""
        activity = self._data.get("status", {}).get("activity", {})
        return PetActivity(
            where=Location(activity.get("where", Location.UNKNOWN.value)),
            since=activity.get("since", None),
        )

    @property
    def feeding(self) -> Optional[StateFeeding]:
        """Last Activity of the Pet."""
        if activity := self._data.get("status", {}).get("feeding", {}):
            return StateFeeding(
                change=activity.get("change", [0.0, 0.0]),
                at=datetime.fromisoformat(activity.get("at", None)),
            )

        return None

    @property
    def drinking(self) -> Optional[StateDrinking]:
        """Last Activity of the Pet."""
        if activity := self._data.get("status", {}).get("drinking", {}):
            return StateDrinking(
                change=activity.get("change", [0.0]),
                at=datetime.fromisoformat(activity.get("at", None)),
            )

        return None

    @property
    def last_lunch(self) -> Optional[datetime]:
        return self.feeding.at if self.feeding else None

    @property
    def last_drink(self) -> Optional[datetime]:
        return self.drinking.at if self.drinking else None
