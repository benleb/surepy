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
from surepy.entities import SurepyDevice, SurepyEntity
from surepy.enums import EntityType
from surepy.flap import Flap
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
    if duration >= 60 * 60:
        if duration_min < 2 or duration_min > 58:
            natural = f"{int(duration_h)}h"
        else:
            natural = f"{int(duration_h)}h {int(duration_min)}min"
    elif duration > 60:
        natural = f"{int(duration_min)}min"
    else:
        natural = f"{int(duration_sec)}sec"

    return natural


# def token_seems_valid(token: str) -> bool:
#     """check validity of an api token based on its characters and length

#     Args:
#         token (str): sure petcare api token

#     Returns:
#         bool: True if ``token`` seems valid
#     """
#     return (
#         (token is not None) and token.isascii() and token.isprintable() and (320 < len(token) < 448)
#     )


# def find_token() -> Optional[str]:

#     token: Optional[str] = None

#     # check env token
#     if (env_token := environ.get(TOKEN_ENV, None)) and token_seems_valid(token=env_token):
#         token = env_token

#     # check file token
#     elif (
#         TOKEN_FILE.exists()
#         and (file_token := TOKEN_FILE.read_text(encoding="utf-8"))
#         and token_seems_valid(token=file_token)
#     ):
#         token = file_token

#     return token


# class SureAPIClient:
#     """Communication with the Sure Petcare API."""

#     def __init__(
#         self,
#         email: Optional[str] = None,
#         password: Optional[str] = None,
#         loop: Optional[asyncio.AbstractEventLoop] = None,
#         session: Optional[aiohttp.ClientSession] = None,
#         auth_token: Optional[str] = None,
#         api_timeout: int = API_TIMEOUT,
#     ) -> None:
#         """Initialize the connection to the Sure Petcare API."""
#         self._loop = loop or asyncio.get_event_loop()
#         self._session = session or aiohttp.ClientSession(
#             connector=aiohttp.TCPConnector(verify_ssl=False)
#         )
#         # self._session = session or aiohttp.ClientSession()

#         # sure petcare credentials
#         self.email = email
#         self.password = password
#         # random device id
#         self._device_id: str = str(uuid1())

#         # connection settings
#         self._api_timeout: int = api_timeout

#         # api token management
#         self._auth_token: Optional[str] = None
#         if auth_token and token_seems_valid(auth_token):
#             self._auth_token = auth_token
#         elif token := find_token():
#             self._auth_token = token
#         # elif token := await self._get_token():
#         #     self._auth_token = token
#         else:
#             # no valid credentials/token
#             SurePetcareAuthenticationError("sorry 🐾 no valid credentials/token found ¯\\_(ツ)_/¯")

#         # storage for received api data
#         self._resource: Dict[str, Any] = {}
#         # storage for etags
#         self._etags: Dict[str, str] = {}

#         logger.debug("initialization completed | vars(): %s", vars())


class SurePetcare:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        # loop: Optional[asyncio.AbstractEventLoop] = None,
        # session: Optional[aiohttp.ClientSession] = None,
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

        # storage for received api data
        self._resource: Dict[str, Any] = {}
        # storage for etags
        self._etags: Dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> Optional[str]:
        return self._auth_token

    @property
    async def devices(self) -> Dict[int, SurepyDevice]:
        return await self.get_entities("devices")

    async def device(self, device_id: int) -> Optional[Union[SurepyDevice, Flap]]:
        return (await self.devices).get(device_id)

    @property
    async def feeders(self) -> Dict[int, Any]:
        return {
            dev.id: dev for dev in (await self.devices).values() if dev.type in [EntityType.FEEDER]
        }

    async def feeder(self, feeder_id: int) -> Optional[Dict[int, Any]]:
        return (await self.feeders).get(feeder_id)

    @property
    async def flaps(self) -> Dict[int, Any]:
        return {
            dev.id: dev
            for dev in (await self.devices).values()
            if dev.type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]
        }

    async def flap(self, flap_id: int) -> Optional[Flap]:
        return (await self.flaps).get(flap_id)

    @property
    async def hubs(self) -> Dict[int, Any]:
        hubs = {}
        for device in (await self.devices).values():
            if device.type == EntityType.HUB:
                hubs[device.id] = device

        return hubs

    async def hub(self, hub_id: int) -> Dict[str, Any]:
        return (await self.flaps).get(hub_id, {})

    @property
    async def pets(self) -> Dict[int, Pet]:
        return await self.get_entities("pets")

    async def pet(self, pet_id: int) -> Pet:
        return (await self.pets)[pet_id]

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
        """Retrieve the flap data/state."""
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

    async def get_entities(self, sure_type: str, refresh: bool = False) -> Dict[int, Any]:

        if MESTART_RESOURCE not in self._resource or refresh:
            await self.sac.call(method="GET", resource=MESTART_RESOURCE)

        entities: Dict[int, Any] = {}
        sure_entities: Dict[EntityType, Dict[int, Union[SurepyEntity, SurepyDevice]]] = {}

        if data := self.sac.resources[MESTART_RESOURCE].get("data", {}).get(sure_type):

            for entity in data:

                entity_type = EntityType(int(entity.get("product_id", 0)))

                surepy_entity: Union[Pet, Flap]

                if entity_type in [EntityType.CAT_FLAP, EntityType.PET_FLAP]:
                    surepy_entity = Flap(data=entity, entity_type=entity_type, sac=self.sac)
                elif entity_type == EntityType.PET:
                    surepy_entity = Pet(data=entity, sac=self.sac)
                else:
                    continue

                entities[entity["id"]] = entity

                if entity_type not in sure_entities:
                    sure_entities[entity_type] = {}

                sure_entities[entity_type][entity["id"]] = surepy_entity

        if sure_type == "devices":
            flaps = sure_entities[EntityType.CAT_FLAP].copy()
            flaps.update(sure_entities[EntityType.PET_FLAP])
            return flaps
        # elif sure_type == "pets":
        #     sure_entities[EntityType.PET]
        else:
            return sure_entities[EntityType.PET]
