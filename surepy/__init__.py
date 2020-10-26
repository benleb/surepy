"""
surepy
====================================
The core module of surepy

|license-info|
"""

import asyncio
import logging

from enum import IntEnum
from importlib.metadata import version
from logging import Logger
from os import environ
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid1

import aiohttp
import async_timeout
import requests


__version__ = version(__name__)

# User-Agent string
_USER_AGENT = (
    "Mozilla/7.0 (Linux; Android 9.0; SX-G730F Build/NRD90M; wv) "
    "AppleWebKit/637.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/84.0.3282.137 Mobile Safari/637.36"
)

# Sure Petcare API endpoints
BASE_RESOURCE: str = "https://app.api.surehub.io/api"
AUTH_RESOURCE: str = f"{BASE_RESOURCE}/auth/login"
MESTART_RESOURCE: str = f"{BASE_RESOURCE}/me/start"
TIMELINE_RESOURCE: str = f"{BASE_RESOURCE}/timeline"
NOTIFICATION_RESOURCE: str = f"{BASE_RESOURCE}/notification"
CONTROL_RESOURCE: str = "{BASE_RESOURCE}/device/{device_id}/control"

API_TIMEOUT = 15

# HTTP constants
ACCEPT = "Accept"
ACCEPT_ENCODING = "Accept-Encoding"
ACCEPT_LANGUAGE = "Accept-Language"
AUTHORIZATION = "Authorization"
CONNECTION = "Connection"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT_PLAIN = "text/plain"
ETAG = "Etag"
HOST = "Host"
HTTP_HEADER_X_REQUESTED_WITH = "X-Requested-With"
ORIGIN = "Origin"
REFERER = "Referer"
USER_AGENT = "User-Agent"

TOKEN_ENV = "SUREPY_TOKEN"
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


def token_seems_valid(token: str) -> bool:
    """check validity of an api token based on its characters and length

    Args:
        token (str): sure petcare api token

    Returns:
        bool: True if ``token`` seems valid
    """
    return (token is not None) and token.isascii() and token.isprintable() and (320 < len(token) < 448)


def find_token() -> Optional[str]:

    token: Optional[str] = None

    # check env token
    if (env_token := environ.get(TOKEN_ENV, None)) and token_seems_valid(token=env_token):
        token = env_token

    # check file token
    elif (
        TOKEN_FILE.exists()
        and (file_token := TOKEN_FILE.read_text(encoding="utf-8"))
        and token_seems_valid(token=file_token)
    ):
        token = file_token

    return token


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
        self._session = session or aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
        # self._session = session or aiohttp.ClientSession()

        # sure petcare credentials
        self.email = email
        self.password = password
        # random device id
        self._device_id: str = str(uuid1())

        # connection settings
        self._api_timeout: int = api_timeout

        # api token management
        self._auth_token: Optional[str] = None
        if auth_token and token_seems_valid(auth_token):
            self._auth_token = auth_token
        else:  # if token := find_token():
            self._auth_token = find_token()
        # elif token := await self._get_token():
        #     self._auth_token = token
        # else:
        #     # no valid credentials/token
        #     SurePetcareAuthenticationError("sorry 🐾 no valid credentials/token found ¯\\_(ツ)_/¯")

        # storage for received api data
        self._resource: Dict[str, Any] = {}
        # storage for etags
        self._etags: Dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    @property
    def auth_token(self) -> Optional[str]:
        return self._auth_token

    @property
    async def devices(self) -> Dict[int, Dict[str, Any]]:
        return await self.get_entities("devices")

    async def device(self, device_id: int) -> Dict[str, Any]:
        device: Dict[str, Any] = (await self.devices).get(device_id, {})
        return device if device else {}

    @property
    async def feeders(self) -> Dict[int, Any]:
        return {dev["id"]: dev for dev in (await self.devices).values() if dev["product_id"] in [SurepyProduct.FEEDER]}

    async def feeder(self, feeder_id: int) -> Optional[Dict[int, Any]]:
        return (await self.feeders).get(feeder_id)

    @property
    async def flaps(self) -> Dict[int, Any]:
        return {
            dev["id"]: dev
            for dev in (await self.devices).values()
            if dev["product_id"] in [SurepyProduct.CAT_FLAP, SurepyProduct.PET_FLAP]
        }

    async def flap(self, flap_id: int) -> Optional[Dict[int, Any]]:
        return (await self.flaps).get(flap_id)

    @property
    async def hubs(self) -> Dict[int, Any]:
        hubs = {}
        for device in (await self.devices).values():
            if device["product_id"] == SurepyProduct.HUB:
                hubs[device["id"]] = device

        return hubs

    async def hub(self, hub_id: int) -> Dict[str, Any]:
        return (await self.flaps).get(hub_id, {})

    @property
    async def pets(self) -> Dict[int, Any]:
        return await self.get_entities("pets")

    async def pet(self, pet_id: int) -> Dict[str, Any]:
        return (await self.pets).get(pet_id, {})

    async def get_timeline(self, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self._get_resource(resource=TIMELINE_RESOURCE)

    async def get_notification(self, second_try: bool = False) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        return await self._get_resource(resource=NOTIFICATION_RESOURCE, timeout=API_TIMEOUT * 2)

    async def get_report(
        self, household_id: int, pet_id: Optional[int] = None, second_try: bool = False
    ) -> Dict[str, Any]:
        """Retrieve the flap data/state."""
        if pet_id:
            return await self._get_resource(resource=f"{BASE_RESOURCE}/report/household/{household_id}/pet/{pet_id}")
        else:
            return await self._get_resource(resource=f"{BASE_RESOURCE}/report/household/{household_id}")

    async def get_entities(self, sure_type: str, refresh: bool = False) -> Dict[int, Any]:

        if MESTART_RESOURCE not in self._resource or refresh:
            await self._get_resource(resource=MESTART_RESOURCE)

        entities: Dict[int, Any] = {}

        if data := self._resource[MESTART_RESOURCE].get("data", {}).get(sure_type):

            for entity in data:
                entities[entity["id"]] = entity

        return entities

    async def _get_resource(
        self, resource: str, timeout: int = API_TIMEOUT, second_try: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        """Retrieve the flap data/state."""

        logger.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            self.get_token()

        data: Dict[str, Any] = {}

        try:
            with async_timeout.timeout(timeout, loop=self._loop):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    logger.info("using available etag '%s' in headers: %s", ETAG, headers)

                logger.debug("headers: %s", headers)

                await self._session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await self._session.get(resource, headers=headers, timeout=timeout)

                logger.debug("response.status: %d", response.status)

            if response.status == 200:

                self._resource[resource] = data = await response.json()

                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data available
                pass

            elif response.status == 401:
                logger.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = self.get_token()
                    if token_refreshed:
                        await self._get_resource(resource=resource, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                logger.info("Response from %s:\n%s", resource, response)
                self._resource[resource] = {}

            return data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            logger.error("Can not load data from %s", resource)
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

        logger.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            # await self._refresh_token()
            self._auth_token = self.get_token()

        response_data: Dict[str, Any] = {}

        try:
            with async_timeout.timeout(self._api_timeout, loop=self._loop):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    logger.debug("using available etag '%s' in headers: %s", ETAG, headers)

                logger.debug("headers: %s", headers)

                await self._session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await self._session.put(resource, headers=headers, data=data)

                logger.debug("response.status: %d", response.status)

            if response.status == 200:

                raw_data = await response.json()

                response_data = raw_data["data"]

                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data available
                pass

            elif response.status == 401:
                logger.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = self.get_token()
                    if token_refreshed:
                        await self._get_resource(resource=resource, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                logger.info("Response from %s:\n%s", resource, response)

            return response_data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            logger.error("Can not load data from %s", resource)
            raise SurePetcareConnectionError()

    def get_token(self) -> Optional[str]:
        """Get or refresh the authentication token."""
        authentication_data: Dict[str, Optional[str]] = dict(
            email_address=self.email, password=self.password, device_id=self._device_id
        )

        token: Optional[str] = None

        try:
            raw_response: requests.Response = requests.post(
                url=AUTH_RESOURCE, data=authentication_data, headers=self._generate_headers()
            )

            if raw_response.status_code == 200:

                response: Dict[str, Any] = raw_response.json()

                if "data" in response and "token" in response["data"]:
                    token = self._auth_token = response["data"]["token"]

            elif raw_response.status_code == 304:
                # Etag header matched, no new data available
                pass

            elif raw_response.status_code == 401:
                self._auth_token = None
                raise SurePetcareAuthenticationError()

            else:
                logger.debug("Response from %s: %s", AUTH_RESOURCE, raw_response)
                raise SurePetcareError()

            return token

        except asyncio.TimeoutError as error:
            logger.debug("Timeout while calling %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareConnectionError()
        except (aiohttp.ClientError, AttributeError) as error:
            logger.debug("Failed to fetch %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareError()

    async def close_session(self) -> None:
        """close the aiohttp.ClientSession (without exposing self._session)"""
        await self._session.close()

    def _generate_headers(self) -> Dict[str, str]:
        """Build a HTTP header accepted by the API"""
        return {
            HOST: "app.api.surehub.io",
            CONNECTION: "keep-alive",
            ACCEPT: f"{CONTENT_TYPE_JSON}, {CONTENT_TYPE_TEXT_PLAIN}, */*",
            ORIGIN: "https://surepetcare.io",
            USER_AGENT: _USER_AGENT,
            REFERER: "https://surepetcare.io/",
            ACCEPT_ENCODING: "gzip, deflate",
            ACCEPT_LANGUAGE: "en-US,en-GB;q=0.9",
            HTTP_HEADER_X_REQUESTED_WITH: "com.sureflap.surepetcare",
            AUTHORIZATION: f"Bearer {self._auth_token}",
            "X-Device-Id": self._device_id,
        }


class SurepyProduct(IntEnum):
    """Sure Petcare API Product IDs."""

    PET = 0  # artificial ID, not used by the Sure Petcare API
    HUB = 1  # Hub
    REPEATER = 2  # Repeater
    PET_FLAP = 3  # Pet Door Connect
    FEEDER = 4  # Microchip Pet Feeder Connect
    PROGRAMMER = 5  # Programmer
    CAT_FLAP = 6  # Cat Flap Connect


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
