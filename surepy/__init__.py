"""
surepy

MIT License
Copyright (c) 2018 Ben Lebherz <git@benleb.de>
"""

from importlib.metadata import version

import asyncio
import logging
import random

from enum import IntEnum
from typing import Any, Dict, Mapping, Optional

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
DATA_RESOURCE: str = f"{BASE_RESOURCE}/me/start"

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

# get a logger
_LOGGER = logging.getLogger(__name__)


class SurePetcare:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: str,
        password: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        session: Optional[aiohttp.ClientSession] = None,
        auth_token: Optional[str] = None,
        api_timeout: Optional[int] = API_TIMEOUT,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""
        self._loop = loop or asyncio.get_event_loop()
        self._session = session or aiohttp.ClientSession()

        self.email = email
        self.password = password

        self._api_timeout = api_timeout
        self._device_id = self._generate_device_id()
        self._auth_token: Optional[str] = auth_token
        self._etag = None

        self.data: Optional[Dict[str, Any]] = dict()

        _LOGGER.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> Optional[str]:
        return self._auth_token

    @property
    async def devices(self) -> Mapping[int, Any]:
        return await self.get_entities("devices")

    async def device(self, device_id: int) -> Optional[Mapping[str, Any]]:
        return (await self.devices).get(device_id)

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

    async def hub(self, hub_id: int) -> Optional[Mapping[int, Any]]:
        return (await self.flaps).get(hub_id)

    @property
    async def pets(self) -> Mapping[int, Any]:
        return await self.get_entities("pets")

    async def pet(self, pet_id: int) -> Optional[Mapping[int, Any]]:
        return (await self.pets).get(pet_id)

    async def get_entities(self, sure_type: str) -> Mapping[int, Any]:
        if not self.data:
            await self.get_data()

        entities = {}
        if self.data and sure_type in self.data:
            for entity in self.data[sure_type]:
                entities[entity["id"]] = entity

        return entities

    async def get_data(self, second_try: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""

        _LOGGER.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            await self._refresh_token()

        try:
            with async_timeout.timeout(self._api_timeout, loop=self._loop):
                headers = self._generate_headers()
                if self._etag:
                    headers[ETAG] = self._etag
                    _LOGGER.debug("using available %s in headers: %s", ETAG, headers)

                _LOGGER.debug("headers: %s", headers)

                response: aiohttp.ClientResponse = await self._session.get(DATA_RESOURCE, headers=headers)

                _LOGGER.debug("response.status: %d", response.status)

            if response.status == 200:

                raw_data = await response.json()
                self.data = raw_data["data"]

                if ETAG in response.headers:
                    self._etag = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data available
                pass

            elif response.status == 401:
                _LOGGER.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = await self._refresh_token()
                    if token_refreshed:
                        await self.get_data(second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.info("Response from %s:\n%s", DATA_RESOURCE, response)
                self.data = None

            return self.data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load data from %s", DATA_RESOURCE)
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
        }

    @staticmethod
    def _generate_device_id() -> str:
        """Generate a "unique" client device ID based on MAC address."""
        random_bytes = ":".join(("%12x" % random.randint(0, 0xFFFFFFFFFFFF))[i : i + 2] for i in range(0, 12, 2))

        mac_dec = int(random_bytes.replace(":", "").replace("-", "").replace(" ", "0"), 16)

        # use low order bits because upper two octets are low entropy
        return str(mac_dec)[-10:]


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


class SurePetcareError(Exception):
    """General Sure Petcare Error exception occurred."""


class SurePetcareConnectionError(SurePetcareError):
    """When a connection error is encountered."""


class SurePetcareAuthenticationError(SurePetcareError):
    """When a authentication error is encountered."""
