"""
surepy

MIT License
Copyright (c) 2018 Benjamin Lebherz <git@benleb.de>
"""

import asyncio
import logging
import random

import aiohttp
import async_timeout

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


_LOGGER = logging.getLogger(__name__)


_USER_AGENT = "Mozilla/5.0 (Linux; Android 7.0; SM-G930F Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/64.0.3282.137 Mobile Safari/537.36"
_RESOURCE: str = "https://app.api.surehub.io/api"
_RESOURCES: dict = dict(
    auth=f"{_RESOURCE}/auth/login",
    device="{}{}".format(_RESOURCE, "/device/{flap_id}/status"),
    household="{}{}".format(_RESOURCE, "/household/{household_id}/position"),
    pet="{}{}".format(_RESOURCE, "/pet/{pet_id}/position"),
    timeline="{}{}".format(_RESOURCE, "/timeline/household/{household_id}"),
)


class SurePetcare:
    """Communication with the Sure Petcare API."""

    def __init__(self, email, password, household_id, loop, session, auth_token=None):
        """Initialize the connection to the Sure Petcare API."""
        self._loop = loop
        self._session = session

        self.email = email
        self.password = password
        self.household_id = household_id

        self._device_id = self._generate_device_id()
        self._auth_token = auth_token

        self.flap_data = dict()
        self.pet_data = dict()

        _LOGGER.debug(f"initialization completed | vars(): {vars()}")

    async def refresh_token(self) -> str:
        """Get or refresh the authentication token."""
        authentication_data = dict(
            email_address=self.email, password=self.password, device_id=self._device_id
        )

        try:
            with async_timeout.timeout(5, loop=self._loop):
                response: aiohttp.ClientResponse = await self._session.post(
                    _RESOURCES["auth"],
                    data=authentication_data,
                    headers=self._generate_headers(),
                )

            if response.status == 200:

                response = await response.json()

                if "data" in response and "token" in response["data"]:
                    self._auth_token = response["data"]["token"]
                    # return True

            elif response.status == 304:
                # Etag header matched, no new data avaiable
                pass

            elif response.status == 401:
                self._auth_token = None
                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.debug(f"Response from {_RESOURCES['auth']}: {response}")
                self._auth_token = None

            return self._auth_token

        except (asyncio.TimeoutError, aiohttp.ClientError, AttributeError) as error:
            _LOGGER.debug("Failed to fetch %s: %s", _RESOURCES["auth"], error)

    async def get_flap_data(self, flap_id, second_try=False) -> dict:
        """Retrieve the flap data/state."""
        device_resource = _RESOURCES["device"].format(flap_id=flap_id)

        if flap_id not in self.flap_data:
            self.flap_data[flap_id] = dict()

        _LOGGER.debug(f"self._auth_token: {self._auth_token}")
        if not self._auth_token:
            await self.refresh_token()

        try:
            with async_timeout.timeout(5, loop=self._loop):
                headers = self._generate_headers()
                if ETAG in self.flap_data[flap_id]:
                    headers[ETAG] = self.flap_data[flap_id][ETAG]
                    _LOGGER.debug(f"using available {ETAG} in headers: {headers}")

                _LOGGER.debug(f"headers: {headers}")

                response: aiohttp.ClientResponse = await self._session.get(
                    device_resource, headers=headers
                )

                _LOGGER.debug(f"\n\n response.status: {response.status}\n\n")

            if response.status == 200:

                self.flap_data[flap_id] = await response.json()

                if ETAG in response.headers:
                    self.flap_data[flap_id][ETAG] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data avaiable
                pass

            elif response.status == 401:
                _LOGGER.debug(f"AuthenticationError! Retry: {second_try}: {response}")
                self._auth_token = None
                if not second_try:
                    token_refreshed = await self.refresh_token()
                    if token_refreshed:
                        await self.get_flap_data(flap_id, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.debug(f"Response from {device_resource}: {response}")
                self.flap_data[flap_id] = None

            return self.flap_data[flap_id]

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error(f"Can not load data from {device_resource}")
            raise SurePetcareConnectionError()

    async def get_pet_data(self, pet_id, second_try=False) -> dict:
        """Retrieve the flap data/state."""
        device_resource = _RESOURCES["pet"].format(pet_id=pet_id)

        if pet_id not in self.pet_data:
            self.pet_data[pet_id] = dict()

        _LOGGER.debug(f"self._auth_token: {self._auth_token}")
        if not self._auth_token:
            await self.refresh_token()

        try:
            with async_timeout.timeout(5, loop=self._loop):
                headers = self._generate_headers()
                if ETAG in self.pet_data[pet_id]:
                    headers[ETAG] = self.pet_data[pet_id][ETAG]
                    _LOGGER.debug(f"using available {ETAG} in headers: {headers}")

                _LOGGER.debug(f"headers: {headers}")

                response: aiohttp.ClientResponse = await self._session.get(
                    device_resource, headers=headers
                )

                _LOGGER.debug(f"\n\n response.status: {response.status}\n\n")

            if response.status == 200:

                self.pet_data[pet_id] = await response.json()

                if ETAG in response.headers:
                    self.pet_data[pet_id][ETAG] = response.headers[ETAG].strip('"')

            elif response.status == 304:
                # Etag header matched, no new data avaiable
                pass

            elif response.status == 401:
                _LOGGER.debug(f"AuthenticationError! Retry: {second_try}: {response}")
                self._auth_token = None
                if not second_try:
                    token_refreshed = await self.refresh_token()
                    if token_refreshed:
                        await self.get_pet_data(pet_id, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                _LOGGER.debug(f"Response from {device_resource}: {response}")
                self.pet_data[pet_id] = None

            return self.pet_data[pet_id]

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error(f"Can not load data from {device_resource}")
            raise SurePetcareConnectionError()

    def _generate_headers(self):
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
    def _generate_device_id():
        """Generate a "unique" client device ID based on MAC address."""
        random_bytes = ":".join(
            ("%12x" % random.randint(0, 0xFFFFFFFFFFFF))[i: i + 2]
            for i in range(0, 12, 2)
        )

        mac_dec = int(random_bytes.replace(":", "").replace("-", ""), 16)
        # Use low order bits because upper two octets are low entropy
        return str(mac_dec)[-10:]


class SureProductID(IntEnum):
    """Sure Petcare API Product IDs."""

    ROUTER = 1  # Sure Hub
    PET_FLAP = 3  # Pet Door Connect
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


class SureThingID(IntEnum):
    """Sure Petcare thing Types."""

    HUB = 0
    FLAP = 1
    PET = 2


class SurePetcareError(Exception):
    """General Sure Petcare Error exception occurred."""


class SurePetcareConnectionError(SurePetcareError):
    """When a connection error is encountered."""


class SurePetcareAuthenticationError(SurePetcareError):
    """When a authentication error is encountered."""
