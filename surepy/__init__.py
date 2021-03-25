"""
surepy
====================================
The core module of surepy

|license-info|
"""

import logging

from importlib.metadata import version
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Optional, Union
from uuid import uuid1

from surepy.client import SureAPIClient, find_token, token_seems_valid
from surepy.const import (
    API_TIMEOUT,
    BASE_RESOURCE,
    MESTART_RESOURCE,
    NOTIFICATION_RESOURCE,
    TIMELINE_RESOURCE,
)
from surepy.entities import SurepyDevice
from surepy.enums import EntityType
from surepy.devices import Flap, Hub
from surepy.pet import Pet


__version__ = version(__name__)


TOKEN_ENV = "SUREPY_TOKEN"  # nosec
TOKEN_FILE = Path("~/.surepy.token").expanduser()


# get a logger
logger: Logger = logging.getLogger(__name__)


def natural_time(duration: int) -> str:

    duration_h, duration_min = divmod(duration, float(60 * 60))
    duration_min, duration_sec = divmod(duration_min, float(60))

    # append suitable unit
    if duration >= 60 * 60 * 24:
        duration_d, duration_h = divmod(duration_h, float(24))
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


class SurePetcare:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        auth_token: Optional[str] = None,
        api_timeout: int = API_TIMEOUT,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""

        # random device id
        self._device_id: str = str(uuid1())

        self.sac = SureAPIClient(
            email=email, password=password, auth_token=auth_token, api_timeout=api_timeout
        )

        # api token management
        self._auth_token: Optional[str] = None
        if auth_token and token_seems_valid(auth_token):
            self._auth_token = auth_token
        else:  # if token := find_token():
            self._auth_token = find_token()

        self._entities: Dict[int, Any] = {}
        self._pets: Dict[int, Any] = {}
        self._flaps: Dict[int, Any] = {}
        self._feeders: Dict[int, Any] = {}
        self._hubs: Dict[int, Any] = {}

        # storage for received api data
        self._resource: Dict[str, Any] = {}
        # storage for etags
        self._etags: Dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> Optional[str]:
        return self._auth_token

    async def refresh(self) -> bool:
        """Get ..."""
        # return await self.get_entities(EntityType.DEVICES) and await self.get_entities(
        #     EntityType.DEVICES
        # )
        return bool(await self.refresh_entities())

    @property
    def devices(self) -> Dict[int, SurepyDevice]:
        """Get all Devices"""
        devices = dict()
        devices.update(self.flaps)
        devices.update(self.hubs)
        return devices

    def device(self, device_id: int) -> Optional[Union[SurepyDevice, Flap]]:
        """Get a Device by its Id"""
        return self.devices.get(device_id, None)

    @property
    def feeders(self) -> Dict[int, Any]:
        """Get all Feeders"""
        return {dev.id: dev for dev in self._devices.values() if dev.type in [EntityType.FEEDER]}

    def feeder(self, feeder_id: int) -> Optional[Dict[int, Any]]:
        """Get a Feeder by its Id"""
        return self.feeders.get(feeder_id)

    @property
    def flaps(self) -> Dict[int, Any]:
        """Get all Flaps"""
        return {
            dev.id: dev
            for dev in self._flaps.values()
            if dev.type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]
        }

    def flap(self, flap_id: int) -> Optional[Flap]:
        """Get a Flap by its Id"""
        return self.flaps.get(flap_id)

    @property
    def hubs(self) -> Dict[int, Any]:
        """Get all Hubs"""
        hubs = {}
        for device in self._hubs.values():
            if device.type == EntityType.HUB:
                hubs[device.id] = device

        return hubs

    def hub(self, hub_id: int) -> Dict[str, Any]:
        """Get a Hub by its Id"""
        return self.hubs.get(hub_id, {})

    @property
    def pets(self) -> Dict[int, Pet]:
        """Get all Pets"""
        return self._pets

    def pet(self, pet_id: int) -> Pet:
        """Get a Pet by its Id"""
        return self.pets.get(pet_id)

    async def get_timeline(self, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self.sac.call(method="GET", resource=TIMELINE_RESOURCE) or {}

    async def get_notification(self, second_try: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self.sac.call(
            method="GET", resource=NOTIFICATION_RESOURCE, timeout=API_TIMEOUT * 2
        )

    async def get_report(
        self, household_id: int, pet_id: Optional[int] = None, second_try: bool = False
    ) -> Dict[str, Any]:
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

    async def refresh_entities(self, refresh: bool = False) -> None:
        """Get all Entities (Pets/Devices)"""

        if MESTART_RESOURCE not in self._resource or refresh:
            await self.sac.call(method="GET", resource=MESTART_RESOURCE)

        if data := self.sac.resources[MESTART_RESOURCE].get("data", {}):

            # devices
            if devices := data.get(EntityType.DEVICES.name.lower()):

                for device in devices:

                    # key used by sure petcare in api response
                    device_type = EntityType(int(device.get("product_id", 0)))
                    device_id = device["id"]

                    if device_type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]:
                        self._flaps[device_id] = Flap(
                            data=device, entity_type=device_type, sac=self.sac
                        )
                    elif device_type in [EntityType.HUB]:
                        self._hubs[device_id] = Hub(
                            data=device, entity_type=device_type, sac=self.sac
                        )
                    # elif device[device_type] in [EntityType.FEEDER]:
                    #     self._flaps[device_id] = Feeder(
                    #         data=device, entity_type=device_type, sac=self.sac)
                    #     )
            else:
                logger.warning("no device data available")

            # pets
            if pets := data.get(f"{EntityType.PET.name.lower()}s"):
                for pet in pets:
                    self._pets[pet["id"]] = Pet(data=pet, sac=self.sac)
            else:
                logger.warning("no pet data available")
