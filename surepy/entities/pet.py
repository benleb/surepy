"""
surepy.pet
====================================
The `Pet` class of surepy

|license-info|
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
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
    """
    Represents pet. Contains attributes of the pet.

    Attributes obtained through Sure PetCare API and include
     - pet ID (int) provided by Sure PetCare
     - pet type default always "pet"
     - pet data: raw output from Sure PetCare API
     - pet name (string) name of pet
     - pet state (integer in API, string in script), one of "outside" or "home"

    """

    def __init__(self, data: dict[str, Any]):

        super().__init__(data=data)

        self.pet_id: int = int(data["id"])

        self._type: EntityType = EntityType.PET
        self._data: dict[str, Any] = data

        self._name = str(name) if (name := self._data.get("name")) else "Unnamed"

        self.state = PetState(data["status"]) if "status" in data else "Unknown"

    @property
    def id(self) -> int:
        """ID of the household the pet belongs to."""
        return self.pet_id

    @property
    def tag_id(self) -> int | None:
        """ID of the household the pet belongs to."""
        return int(tag_id) if (tag_id := self._data.get("tag_id")) else None

    @property
    def food_type(self) -> str | None:
        """Type of food."""
        return str(FoodType(type_id)) if (type_id := self._data.get("food_type_id")) else None

    @property
    def updated_at(self) -> datetime | None:
        """Type of food."""
        return (
            datetime.fromisoformat(updated_at)
            if (updated_at := self._data.get("updated_at"))
            else None
        )

    @property
    def photo_url(self) -> str | None:
        """Picture of the Pet."""
        picture_url = (
            photo_url
            if (photo_url := self._data.get("photo", {}).get("location"))
            else "https://surehub.io/assets/images/no-pet-pic-dark.svg"
        )

        return urlparse(picture_url).geturl()

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
    def feeding(self) -> StateFeeding | None:
        """Last Activity of the Pet."""
        if activity := self._data.get("status", {}).get("feeding", {}):
            return StateFeeding(
                change=activity.get("change", [0.0, 0.0]),
                at=datetime.fromisoformat(activity.get("at", None)),
            )

        return None

    @property
    def drinking(self) -> StateDrinking | None:
        """Last Activity of the Pet."""
        if activity := self._data.get("status", {}).get("drinking", {}):
            return StateDrinking(
                change=activity.get("change", [0.0]),
                at=datetime.fromisoformat(activity.get("at", None)),
            )

        return None

    @property
    def last_lunch(self) -> datetime | None:
        return self.feeding.at if self.feeding else None

    @property
    def last_drink(self) -> datetime | None:
        return self.drinking.at if self.drinking else None
