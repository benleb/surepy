"""
surepy

MIT License
Copyright (c) 2018 Ben Lebherz <git@benleb.de>
"""

import asyncio
import logging

from enum import IntEnum
from importlib.metadata import version
from os import environ
from typing import Any, Dict, Mapping, Optional, Union
from uuid import UUID, uuid4

import aiohttp
import async_timeout


__version__ = version(__name__)

# User-Agent string
_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 7.0; SM-G930F Build/NRD90M; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/64.0.3282.137 Mobile Safari/537.36"
)

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"

CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"

API_TIMEOUT = 10

# HTTP constants
ACCEPT = "Accept"
ACCEPT_ENCODING = "Accept-Encoding"
ACCEPT_LANGUAGE = "Accept-Language"
AUTHORIZATION = "Authorization"
CONNECTION = "Connection"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT_PLAIN = "text/plain"
ETAG = "Etag"
HTTP_HEADER_X_REQUESTED_WITH = "X-Requested-With"
ORIGIN = "Origin"
REFERER = "Referer"
USER_AGENT = "User-Agent"

ENV_SUREPY_TOKEN = "SUREPY_TOKEN"

# get a logger
_LOGGER = logging.getLogger(__name__)

_LOGGER.setLevel(logging.DEBUG)


def hl(text: Union[int, float, str]) -> str:
    return f"\033[1m{text}\033[0m"


def hl_entity(entity: str) -> str:
    domain, entity = entity.split(".")
    return f"{domain}.{hl(entity)}"


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


class SureLockStateID(IntEnum):
    """Sure Petcare API State IDs."""

    UNLOCKED = 0
    LOCKED_IN = 1
    LOCKED_OUT = 2
    LOCKED_ALL = 3
    CURFEW = 4
    CURFEW_LOCKED = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN = -3


class SurePetcare:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        session: Optional[aiohttp.ClientSession] = None,
        auth_token: Optional[str] = None,
        api_timeout: int = API_TIMEOUT,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""
        self._loop = loop or asyncio.get_event_loop()
        self._session = session or aiohttp.ClientSession()

        self.email = email
        self.password = password

        self._api_timeout: int = api_timeout
        self._device_id: UUID = uuid4()
        self._auth_token: Optional[str] = auth_token if auth_token else environ.get(ENV_SUREPY_TOKEN)

        self._resource: Dict[str, Any] = {}
        self._etags: Dict[str, str] = {}

        _LOGGER.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> Optional[str]:
        return self._auth_token

    @property
    async def devices(self) -> Mapping[int, Dict[str, Any]]:
        return await self.get_entities("devices")

    async def device(self, device_id: int) -> Dict[str, Any]:
        device: Dict[str, Any] = (await self.devices).get(device_id, {})
        return device if device else {}

    @property
    async def feeders(self) -> Mapping[int, Any]:
        feeders = {}
        for device in (await self.devices).values():
            if device["product_id"] in [SureProductID.FEEDER]:
                feeders[device["id"]] = device

        return feeders

    async def feeder(self, feeder_id: int) -> Optional[Mapping[int, Any]]:
        return (await self.feeders).get(feeder_id)

    @property
    async def flaps(self) -> Mapping[int, Any]:
        flaps = {}
        for device in (await self.devices).values():
            if device["product_id"] in [SureProductID.CAT_FLAP, SureProductID.PET_FLAP]:
                flaps[device["id"]] = device

        return flaps

    async def flap(self, flap_id: int) -> Optional[Mapping[int, Any]]:
        return (await self.flaps).get(flap_id)

    @property
    async def hubs(self) -> Mapping[int, Any]:
        hubs = {}
        for device in (await self.devices).values():
            if device["product_id"] == SureProductID.HUB:
                hubs[device["id"]] = device

        return hubs

    async def hub(self, hub_id: int) -> Dict[str, Any]:
        return (await self.flaps).get(hub_id, {})

    @property
    async def pets(self) -> Mapping[int, Any]:
        return await self.get_entities("pets")

    async def pet(self, pet_id: int) -> Dict[str, Any]:
        return (await self.pets).get(pet_id, {})

    async def get_entities(self, sure_type: str) -> Dict[int, Any]:

        if MESTART_RESOURCE not in self._resource:
            self._resource[MESTART_RESOURCE] = (await self._get_resource(resource=MESTART_RESOURCE)).get("data")

        entities: Dict[int, Any] = {}

        if MESTART_RESOURCE in self._resource and (data := self._resource[MESTART_RESOURCE].get(sure_type)):

            for entity in data:
                entities[entity["id"]] = entity

        return entities

    async def get_timeline(self, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self._get_resource(resource=TIMELINE_RESOURCE)

    async def get_notification(self, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self._get_resource(resource=NOTIFICATION_RESOURCE, timeout=API_TIMEOUT * 2)

    async def get_pet_report(self, pet_id: int, household_id: int, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self._get_resource(resource=f"{BASE_RESOURCE}/report/household/{household_id}/pet/{pet_id}")

    async def get_report(
        self, household_id: int, pet_id: Optional[int] = None, second_try: bool = False
    ) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        if pet_id:
            return await self._get_resource(resource=f"{BASE_RESOURCE}/report/household/{household_id}/pet/{pet_id}")
        else:
            return await self._get_resource(resource=f"{BASE_RESOURCE}/report/household/{household_id}")

    async def _get_resource(
        self, resource: str, timeout: int = API_TIMEOUT, second_try: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        """Retrieve the flap data/state."""

        _LOGGER.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            await self._refresh_token()

        data: Dict[str, Any] = {}

        try:
            with async_timeout.timeout(timeout, loop=self._loop):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    _LOGGER.debug("using available etag '%s' in headers: %s", ETAG, headers)

                _LOGGER.debug("headers: %s", headers)

                await self._session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await self._session.get(resource, headers=headers, timeout=timeout)

                _LOGGER.debug("response.status: %d", response.status)

            if response.status == 200:

                self._resource[resource] = data = await response.json()

                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data available
                pass

            elif response.status == 401:
                _LOGGER.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = await self._refresh_token()
                    if token_refreshed:
                        await self._get_resource(resource=resource, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.info("Response from %s:\n%s", resource, response)
                self._resource[resource] = {}

            return data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from %s", resource)
            raise SurePetcareConnectionError()

    async def lock(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, SureLockStateID.LOCKED_ALL)

    async def lock_in(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, SureLockStateID.LOCKED_IN)

    async def lock_out(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, SureLockStateID.LOCKED_OUT)

    async def unlock(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, SureLockStateID.UNLOCKED)

    async def _locking(self, device_id: int, mode: SureLockStateID) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        resource = CONTROL_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, device_id=device_id)
        data = {"locking": mode.value}

        if response := await self._put_resource(resource=resource, device_id=device_id, data=data):

            if "locking" in response and response["locking"] == data["locking"]:
                return response

        raise SurePetcareError("ERROR UNLOCKING DEVICE - PLEASE CHECK IMMEDIATELY!")

    async def _put_resource(
        self, resource: str, data: Dict[str, Any], second_try: bool = False, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""

        _LOGGER.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            await self._refresh_token()

        response_data: Dict[str, Any] = {}

        try:
            with async_timeout.timeout(self._api_timeout, loop=self._loop):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    _LOGGER.debug("using available etag '%s' in headers: %s", ETAG, headers)

                _LOGGER.debug("headers: %s", headers)

                await self._session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await self._session.put(resource, headers=headers, data=data)

                _LOGGER.debug("response.status: %d", response.status)

            if response.status == 200:

                raw_data = await response.json()

                response_data = raw_data["data"]

                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data available
                pass

            elif response.status == 401:
                _LOGGER.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = await self._refresh_token()
                    if token_refreshed:
                        await self._get_resource(resource=resource, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.info("Response from %s:\n%s", resource, response)
                # self.data = None

            return response_data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from %s", resource)
            raise SurePetcareConnectionError()

    async def _refresh_token(self) -> Optional[str]:
        """Get or refresh the authentication token."""
        authentication_data = dict(email_address=self.email, password=self.password, device_id=self._device_id)

        try:
            with async_timeout.timeout(self._api_timeout, loop=self._loop):
                raw_response: aiohttp.ClientResponse = await self._session.post(
                    AUTH_RESOURCE,
                    data=authentication_data,
                    headers=self._generate_headers(),
                )

            if raw_response.status == 200:

                response: Dict[str, Any] = await raw_response.json()

                if "data" in response and "token" in response["data"]:
                    self._auth_token = response["data"]["token"]

            elif raw_response.status == 304:
                # Etag header matched, no new data available
                pass

            elif raw_response.status == 401:
                self._auth_token = None
                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.debug("Response from %s: %s", AUTH_RESOURCE, raw_response)
                self._auth_token = None
                raise SurePetcareError()

            return self._auth_token

        except asyncio.TimeoutError as error:
            _LOGGER.debug("Timeout while calling %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareConnectionError()
        except (aiohttp.ClientError, AttributeError) as error:
            _LOGGER.debug("Failed to fetch %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareError()

    def _generate_headers(self) -> Dict[str, str]:
        """Build a HTTP header accepted by the API"""
        return {
            CONNECTION: "keep-alive",
            ACCEPT: f"{CONTENT_TYPE_JSON}, {CONTENT_TYPE_TEXT_PLAIN}, */*",
            ORIGIN: "https://surepetcare.io",
            USER_AGENT: _USER_AGENT,
            REFERER: "https://surepetcare.io/",
            ACCEPT_ENCODING: "gzip, deflate",
            ACCEPT_LANGUAGE: "en-US,en-GB;q=0.9",
            HTTP_HEADER_X_REQUESTED_WITH: "com.sureflap.surepetcare",
            AUTHORIZATION: f"Bearer {self._auth_token}",
            # "X-Device-Id": str(uuid.uuid4())
        }


class SureProductID(IntEnum):
    """Sure Petcare API Product IDs."""

    PET = 0  # This ID is artificial and not from Sure Petcare
    HUB = 1  # Sure Hub
    PET_FLAP = 3  # Pet Door Connect
    FEEDER = 4  # Feeder Connect
    CAT_FLAP = 6  # Cat Door Connect


# Thanks to @rcastberg for discovering the IDs used by the Sure Petcare API."""
class SureLocationID(IntEnum):
    """Sure Petcare API Location IDs."""

    INSIDE = 1
    OUTSIDE = 2
    UNKNOWN = -1


class SurePetcareError(Exception):
    """General Sure Petcare Error exception occurred."""


class SurePetcareConnectionError(SurePetcareError):
    """When a connection error is encountered."""


class SurePetcareAuthenticationError(SurePetcareError):
    """When a authentication error is encountered."""
