"""
surepy
====================================
The core module of surepy

|license-info|
"""

from __future__ import annotations

import logging

from datetime import datetime
from importlib.metadata import version
from logging import Logger
from math import ceil
from typing import Any
from uuid import uuid1

import aiohttp

from rich.console import Console

from surepy.client import SureAPIClient, find_token, token_seems_valid
from surepy.const import (
    API_TIMEOUT,
    ATTRIBUTES_RESOURCE as ATTR_RESOURCE,
    BASE_RESOURCE,
    HOUSEHOLD_TIMELINE_RESOURCE,
    MESTART_RESOURCE,
    NOTIFICATION_RESOURCE,
    TIMELINE_RESOURCE,
)
from surepy.entities import SurepyEntity
from surepy.entities.devices import Feeder, Felaqua, Flap, Hub, SurepyDevice
from surepy.entities.pet import Pet
from surepy.enums import EntityType


__version__ = version(__name__)

# TOKEN_ENV = "SUREPY_TOKEN"  # nosec
# TOKEN_FILE = Path("~/.surepy.token").expanduser()

# get a logger
logger: Logger = logging.getLogger(__name__)

console = Console(width=120)


def natural_time(duration: int) -> str:
    """Transforms a number of seconds to a more human-friendly string.

    Args:
        duration (int): duration in seconds

    Returns:
        str: human-friendly duration string
    """

    duration_h, duration_min = divmod(duration, int(60 * 60))
    duration_min, duration_sec = divmod(duration_min, int(60))

    # append suitable unit
    if duration >= 60 * 60 * 24:
        duration_d, duration_h = divmod(duration_h, int(24))
        natural = f"{int(duration_d)}d {int(duration_h)}h {int(duration_min)}m"

    elif duration >= 60 * 60:
        if duration_min < 2 or duration_min > 58:
            natural = f"{int(duration_h)}h"
        else:
            natural = f"{int(duration_h)}h {int(duration_min)}m"

    elif duration > 60:
        natural = f"{int(duration_min)}min"

    else:
        natural = f"{int(duration_sec)}sec"

    return natural


class Surepy:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        auth_token: str | None = None,
        api_timeout: int = API_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""

        # random device id
        self._device_id: str = str(uuid1())

        self._session = session

        self.sac = SureAPIClient(
            email=email,
            password=password,
            auth_token=auth_token,
            api_timeout=api_timeout,
            session=self._session,
            surepy_version=__version__,
        )

        # api token management
        self._auth_token: str | None = None
        if auth_token and token_seems_valid(auth_token):
            self._auth_token = auth_token
        else:  # if token := find_token():
            self._auth_token = find_token()

        self.entities: dict[int, SurepyEntity] = {}
        self._pets: dict[int, Any] = {}
        self._flaps: dict[int, Any] = {}
        self._feeders: dict[int, Any] = {}
        self._hubs: dict[int, Any] = {}

        self._breeds: dict[int, dict[int, Any]] = {}
        self._species_breeds: dict[int, dict[int, Any]] = {}
        self._conditions: dict[int, Any] = {}

        # storage for received api data
        self._resource: dict[str, Any] = {}
        # storage for etags
        self._etags: dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> str | None:
        """Authentication token for device"""
        return self._auth_token

    async def pets_details(self) -> list[dict[str, Any]] | None:
        """Fetch pet information."""
        return await self.sac.get_pets()

    async def latest_actions(self, household_id: int) -> dict[int, dict[str, Any]] | None:
        """
        Args:
            household_id (int): ID associated with household
            pet_id (int): ID associated with pet

        Returns:
            Get the latest action using pet_id and household_id
            from raw data and output as a dictionary
        """
        return await self.get_actions(household_id=household_id)

    async def all_actions(self, household_id: int) -> dict[int, dict[str, Any]] | None:
        """Args:
        - household_id (int): id associated with household
        - pet_id (int): id associated with pet
        """
        return await self.get_actions(household_id=household_id)

    async def get_actions(self, household_id: int) -> dict[int, dict[str, Any]] | None:
        resource = f"{BASE_RESOURCE}/report/household/{household_id}"

        latest_actions: dict[int, dict[str, Any]] = {}

        pet_device_pairs: dict[str, Any] = (
            await self.sac.call(method="GET", resource=resource) or {}
        )

        if "data" not in pet_device_pairs:
            return latest_actions

        data: list[dict[str, Any]] = pet_device_pairs["data"]

        for pair in data:

            pet_id = int(pair["pet_id"])
            device_id = int(pair["device_id"])
            device: SurepyDevice = self.entities[device_id]  # type: ignore

            latest_actions[pet_id] = {}
            latest_actions[pet_id] = self.entities[device_id]._data

            # movement
            if (
                device.type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]
                and pair["movement"]["datapoints"]
            ):
                latest_datapoint = pair["movement"]["datapoints"].pop()
                # latest_actions[pet_id]["move"] = latest_datapoint
                latest_actions[pet_id] = self.entities[device_id]._data["move"] = latest_datapoint

            # feeding
            elif (
                device.type in [EntityType.FEEDER, EntityType.FEEDER_LITE]
                and pair["feeding"]["datapoints"]
            ):
                latest_datapoint = pair["feeding"]["datapoints"].pop()
                # latest_actions[pet_id]["lunch"] = latest_datapoint
                latest_actions[pet_id] = self.entities[device_id]._data["lunch"] = latest_datapoint

            # drinking
            elif device.type == EntityType.FELAQUA and pair["drinking"]["datapoints"]:
                latest_datapoint = pair["drinking"]["datapoints"].pop()
                # latest_actions[pet_id]["drink"] = latest_datapoint
                latest_actions[pet_id] = self.entities[device_id]._data["drink"] = latest_datapoint

        return latest_actions

    async def get_latest_anonymous_drinks(self, household_id: int) -> dict[str, Any] | None:

        latest_drink: dict[str, float | str | datetime] = {}

        household_timeline = await self.get_household_timeline(household_id, entries=50)

        felaqua_related_entries: list[dict[str, Any]] = list(
            filter(
                lambda x: x["type"] in [29, 30, 34],  # type: ignore
                household_timeline,  # type: ignore
            )
        )

        if felaqua_related_entries:
            try:
                device_id = felaqua_related_entries[0]["weights"][0]["device_id"]
                latest_entry_frame = felaqua_related_entries[0]["weights"][0]["frames"][0]
                remaining = latest_entry_frame["current_weight"]
                change = latest_entry_frame["change"]
                updated_at = latest_entry_frame["updated_at"]
                latest_drink = {"remaining": remaining, "change": change, "date": updated_at}

                self.entities[device_id]._data["latest_drink"] = latest_drink

            except (KeyError, TypeError, IndexError):
                logger.warning(
                    "no water remaining/change events found in household timeline "
                    "(checked last %s entries)",
                    len(household_timeline) or 0,
                )

        return latest_drink

    async def get_household_timeline(
        self, household_id: int | None = None, entries: int = 25
    ) -> list[dict[str, Any]]:
        """Fetch Felaqua water level information."""

        # pagination as the api gives us at most 25 results per page
        max_entries_per_page = 25
        pages_to_fetch = ceil(entries / max_entries_per_page)

        current_page = 1
        household_timeline = []

        while current_page <= pages_to_fetch:

            console.print()
            console.print(f"{current_page = }/{pages_to_fetch} | {len(household_timeline) = }")

            resource = HOUSEHOLD_TIMELINE_RESOURCE.format(
                BASE_RESOURCE=BASE_RESOURCE,
                household_id=household_id,
                page=current_page,
                page_size=max_entries_per_page,
            )

            if timeline := await self.sac.call(method="GET", resource=resource):
                household_timeline += timeline.get("data", [])

            current_page += 1

        return household_timeline

    async def get_timeline(self) -> dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self.sac.call(method="GET", resource=TIMELINE_RESOURCE) or {}

    async def get_notification(self) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        return await self.sac.call(
            method="GET", resource=NOTIFICATION_RESOURCE, timeout=API_TIMEOUT * 2
        )

    async def get_report(self, household_id: int, pet_id: int | None = None) -> dict[str, Any]:
        """Retrieve the pet/household report."""
        return (
            await self.sac.call(
                method="GET",
                resource=f"{BASE_RESOURCE}/report/household/{household_id}/pet/{pet_id}",
            )
            if pet_id
            else await self.sac.call(
                method="GET", resource=f"{BASE_RESOURCE}/report/household/{household_id}"
            )
        ) or {}

    async def get_pets(self) -> list[Pet]:
        return [pet for pet in (await self.get_entities()).values() if isinstance(pet, Pet)]

    async def get_device(self, device_id: int) -> SurepyDevice | None:
        if device_id not in self.entities:
            await self.get_entities()

        if self.entities[device_id].type != EntityType.PET:
            return self.entities[device_id]  # type: ignore
        else:
            return None

    async def get_devices(self) -> list[SurepyDevice]:
        return [
            device
            for device in (await self.get_entities()).values()
            if isinstance(device, SurepyDevice)
        ]

    async def get_attributes(self) -> dict[str, Any] | None:
        # fetch additional data from sure petcare
        attributes: dict[str, Any] | None = None

        if (raw_data := (await self.sac.call(method="GET", resource=ATTR_RESOURCE))) and (
            attributes := raw_data.get("data")
        ):

            for breed in attributes.get("breed", {}):
                self._breeds[breed["id"]] = breed["name"]

                if breed["species_id"] not in self._breeds:
                    self._species_breeds[breed["species_id"]] = {}

                self._species_breeds[breed["species_id"]][breed["id"]] = breed["name"]

            for condition in attributes.get("condition", {}):
                self._conditions[condition["id"]] = condition["name"]

        return attributes

    async def get_entities(self, refresh: bool = False) -> dict[int, SurepyEntity]:
        """Get all Entities (Pets/Devices)"""

        household_ids: set[int] = set()
        felaqua_household_ids: set[int] = set()
        surepy_entities: dict[int, SurepyEntity] = {}

        raw_data: dict[str, list[dict[str, Any]]] = {}

        # get data like species, breed, conditions
        # await self.get_attributes()

        if MESTART_RESOURCE not in self.sac.resources or refresh:
            if response := await self.sac.call(method="GET", resource=MESTART_RESOURCE):
                raw_data = response.get("data", {})
        else:
            raw_data = self.sac.resources[MESTART_RESOURCE].get("data", {})

        if not raw_data:
            logger.error("could not fetch data ¯\\_(ツ)_/¯")
            return surepy_entities

        all_entities = raw_data.get("devices", []) + raw_data.get("pets", [])

        for entity in all_entities:

            # key used by sure petcare in api response
            entity_type = EntityType(int(entity.get("product_id", 0)))
            entity_id = entity["id"]

            if entity_type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]:
                surepy_entities[entity_id] = Flap(data=entity)
            elif entity_type in [EntityType.FEEDER, EntityType.FEEDER_LITE]:
                surepy_entities[entity_id] = Feeder(data=entity)
            elif entity_type == EntityType.FELAQUA:
                surepy_entities[entity_id] = Felaqua(data=entity)
                felaqua_household_ids.add(int(surepy_entities[entity_id].household_id))
            elif entity_type == EntityType.HUB:
                surepy_entities[entity_id] = Hub(data=entity)
            elif entity_type == EntityType.PET:
                surepy_entities[entity_id] = Pet(data=entity)

            else:
                logger.warning(
                    f"unknown entity type: {entity.get('name', '-')} ({entity_type}): {entity}"
                )

            household_ids.add(surepy_entities[entity_id].household_id)

            self.entities[entity_id] = surepy_entities[entity_id]

        # fetch additional data about movement, feeding & drinking
        for household_id in household_ids:
            await self.get_actions(household_id=household_id)
        for household_id in felaqua_household_ids:
            await self.get_latest_anonymous_drinks(household_id=household_id)

        # stupid idea, fix this
        _ = [
            feeder.add_bowls()  # type: ignore
            for feeder in surepy_entities.values()
            if feeder.type == EntityType.FEEDER
        ]

        return self.entities
