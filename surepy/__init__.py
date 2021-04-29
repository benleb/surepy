"""
surepy
====================================
The core module of surepy

|license-info|
"""

from __future__ import annotations

import logging

from importlib.metadata import version
from logging import Logger
from typing import Any
from uuid import uuid1

import aiohttp

from surepy.client import SureAPIClient, find_token, token_seems_valid
from surepy.const import (
    API_TIMEOUT,
    BASE_RESOURCE,
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

        self._entities: dict[int, Any] = {}
        self._pets: dict[int, Any] = {}
        self._flaps: dict[int, Any] = {}
        self._feeders: dict[int, Any] = {}
        self._hubs: dict[int, Any] = {}

        # storage for received api data
        self._resource: dict[str, Any] = {}
        # storage for etags
        self._etags: dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> str | None:
        return self._auth_token

    # async def refresh(self) -> bool:
    #     """Get ..."""
    #     return await self.sac.get_entities(EntityType.DEVICES) and await self.get_entities(
    #         EntityType.DEVICES
    #     )
    #     # return bool(await self.refresh_entities())

    # @property
    # def devices(self) -> Set[SurepyDevice]:
    #     """Get all Devices"""
    #     all_devices = set()
    #     all_devices.update(self.flaps)
    #     all_devices.update(self.hubs)
    #     return all_devices

    # def device(self, device_id: int) -> Optional[Union[SurepyDevice, Flap]]:
    #     """Get a Device by its Id"""
    #     return self.devices.get(device_id, None)
    #
    # @property
    # def feeders(self) -> dict[int, Any]:
    #     """Get all Feeders"""
    #     return {dev.id: dev for dev in self._devices.values() if dev.type in [EntityType.FEEDER]}
    #
    # def feeder(self, feeder_id: int) -> Optional[dict[int, Any]]:
    #     """Get a Feeder by its Id"""
    #     return self.feeders.get(feeder_id)

    # @property
    # def flaps(self) -> Set[Flap]:
    #     """Get all Flaps"""
    #     return {
    #         dev.id: dev
    #         for dev in self._flaps.values()
    #         if dev.type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]
    #     }
    #
    # def flap(self, flap_id: int) -> Optional[Flap]:
    #     """Get a Flap by its Id"""
    #     return self.flaps.get(flap_id)

    # @property
    # def hubs(self) -> dict[int, Any]:
    #     """Get all Hubs"""
    #     hubs = {}
    #     for device in self._hubs.values():
    #         if device.type == EntityType.HUB:
    #             hubs[device.id] = device
    #
    #     return hubs
    #
    # def hub(self, hub_id: int) -> dict[str, Any]:
    #     """Get a Hub by its Id"""
    #     return self.hubs.get(hub_id, {})

    # @property
    # def pets(self) -> dict[int, Pet]:
    #     """Get all Pets"""
    #     return self._pets
    #
    # def pet(self, pet_id: int) -> Pet:
    #     """Get a Pet by its Id"""
    #     return self.pets.get(pet_id)

    async def pets_details(self) -> list[dict[str, Any]] | None:
        """Fetch pet information."""
        return await self.sac.get_pets()

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

    async def get_devices(self) -> list[SurepyDevice]:
        return [
            device
            for device in (await self.get_entities()).values()
            if isinstance(device, SurepyDevice)
        ]

    async def get_entities(self, refresh: bool = False) -> dict[int, SurepyEntity]:
        """Get all Entities (Pets/Devices)"""

        # if MESTART_RESOURCE not in self._resource or refresh:
        if MESTART_RESOURCE not in self.sac.resources or refresh:
            await self.sac.call(method="GET", resource=MESTART_RESOURCE)

        raw_data: dict[str, list[dict[str, Any]]]

        surepy_entities: dict[int, SurepyEntity] = {}

        if raw_data := self.sac.resources[MESTART_RESOURCE].get("data", {}):

            for entity in raw_data.get("devices", []) + raw_data.get("pets", []):

                # key used by sure petcare in api response
                entity_type = EntityType(int(entity.get("product_id", 0)))
                entity_id = entity["id"]

                if entity_type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]:
                    surepy_entities[entity_id] = Flap(data=entity)
                elif entity_type in [EntityType.FEEDER, EntityType.FEEDER_LITE]:
                    surepy_entities[entity_id] = Feeder(data=entity)
                elif entity_type == EntityType.FELAQUA:
                    surepy_entities[entity_id] = Felaqua(data=entity)
                elif entity_type == EntityType.HUB:
                    surepy_entities[entity_id] = Hub(data=entity)
                elif entity_type == EntityType.PET:
                    surepy_entities[entity_id] = Pet(data=entity)

                else:
                    logger.warning(
                        f"unknown entity type: {entity.get('name', '-')} ({entity_type}): {entity}"
                    )

        return surepy_entities

    # async def get_devices(self) -> dict[int, SurepyEntity]:
    #     """Retrieve the pet data/state."""

    #     devices: dict[int, SurepyEntity] = {}

    #     response: Optional[dict[str, Any]] = await self.sac.call(
    #         method="GET", resource=DEVICE_RESOURCE
    #     )

    #     if data := response.get("data"):

    #         for raw_entity in data:

    #             entity_type: Optional[EntityType] = None

    #             # key used by sure petcare in api response
    #             try:
    #                 entity_type = EntityType(int(raw_entity.get("product_id")))
    #             except Exception as error:
    #                 logger.error(f"error reading entity properties from response: {error}")

    #             if entity_type and (entity_id := raw_entity.get("id")):

    #                 if entity_type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]:
    #                     devices[entity_id] = Flap(data=raw_entity)
    #                 if entity_type in [EntityType.FEEDER, EntityType.FEEDER_LITE]:
    #                     devices[entity_id] = Feeder(data=raw_entity)
    #                 if entity_type == EntityType.FELAQUA:
    #                     devices[entity_id] = Felaqua(data=raw_entity)
    #                 elif entity_type == EntityType.HUB:
    #                     devices[entity_id] = Hub(data=raw_entity)

    #     return devices
