"""
surepy
====================================
The core module of surepy

|license-info|
"""

from __future__ import annotations

import asyncio
import logging

from datetime import datetime
from http import HTTPStatus
from http.client import HTTPException
from logging import Logger
from os import environ
from pathlib import Path
from typing import Any
from uuid import uuid1

import aiohttp
import async_timeout

from .const import (
    ACCEPT,
    ACCEPT_ENCODING,
    ACCEPT_LANGUAGE,
    API_TIMEOUT,
    AUTH_RESOURCE,
    AUTHORIZATION,
    BASE_RESOURCE,
    CONNECTION,
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_TEXT_PLAIN,
    CONTROL_RESOURCE,
    ETAG,
    HOST,
    HTTP_HEADER_X_REQUESTED_WITH,
    ORIGIN,
    PET_RESOURCE,
    POSITION_RESOURCE,
    REFERER,
    SUREPY_USER_AGENT,
    USER_AGENT,
)
from .enums import Location, LockState
from .exceptions import SurePetcareAuthenticationError, SurePetcareConnectionError, SurePetcareError


TOKEN_ENV = "SUREPY_TOKEN"
TOKEN_FILE = Path("~/.surepy.token").expanduser()

# get a logger
logger: Logger = logging.getLogger(__name__)


def token_seems_valid(token: str) -> bool:
    """check validity of an api token based on its characters and length

    Args:
        token (str): sure petcare api token

    Returns:
        bool: True if ``token`` seems valid
    """
    return (
        (token is not None) and token.isascii() and token.isprintable() and (320 < len(token) < 448)
    )


def find_token() -> str | None:
    token: str | None = None

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


class SureAPIClient:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        # loop: Optional[asyncio.AbstractEventLoop] = None,
        auth_token: str | None = None,
        api_timeout: int = API_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
        surepy_version: str | None = None,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""

        self._session = session

        # sure petcare credentials
        self.email = email
        self.password = password
        # random device id
        self._device_id: str = str(uuid1())

        # connection settings
        self._api_timeout: int = api_timeout

        self._surepy_version: str | None = surepy_version

        # api token management
        self._auth_token: str | None = None
        if auth_token and token_seems_valid(auth_token):
            self._auth_token = auth_token
        elif token := find_token():
            self._auth_token = token
        else:
            # no valid credentials/token
            SurePetcareAuthenticationError("sorry 🐾 no valid credentials/token found ¯\\_(ツ)_/¯")

        # storage for received api data
        self.resources: dict[str, Any] = {}
        # storage for etags
        self._etags: dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

    def _generate_headers(self) -> dict[str, str]:
        """Build a HTTP header accepted by the API"""
        user_agent = (
            SUREPY_USER_AGENT.format(version=self._surepy_version) if self._surepy_version else None
        )

        return {
            HOST: "app.api.surehub.io",
            CONNECTION: "keep-alive",
            ACCEPT: f"{CONTENT_TYPE_JSON}, {CONTENT_TYPE_TEXT_PLAIN}, */*",
            ORIGIN: "https://surepetcare.io",
            USER_AGENT: user_agent if user_agent else SUREPY_USER_AGENT,
            REFERER: "https://surepetcare.io",
            ACCEPT_ENCODING: "gzip, deflate",
            ACCEPT_LANGUAGE: "en-US,en-GB;q=0.9",
            HTTP_HEADER_X_REQUESTED_WITH: "com.sureflap.surepetcare",
            AUTHORIZATION: f"Bearer {self._auth_token}",
            "X-Device-Id": self._device_id,
        }

    async def get_token(self) -> str | None:
        """Get or refresh the authentication token."""
        authentication_data: dict[str, str | None] = dict(
            email_address=self.email, password=self.password, device_id=self._device_id
        )

        token: str | None = None

        session = self._session if self._session else aiohttp.ClientSession()

        try:
            raw_response: aiohttp.ClientResponse = await session.post(
                url=AUTH_RESOURCE, data=authentication_data, headers=self._generate_headers()
            )

            if raw_response.status == HTTPStatus.OK:

                response: dict[str, Any] = await raw_response.json()

                if "data" in response and "token" in response["data"]:
                    token = self._auth_token = response["data"]["token"]

            elif raw_response.status == HTTPStatus.NOT_MODIFIED:
                # Etag header matched, no new data available
                pass

            elif raw_response.status == HTTPStatus.UNAUTHORIZED:
                self._auth_token = None
                raise SurePetcareAuthenticationError()

            else:
                logger.debug("Response from %s: %s", AUTH_RESOURCE, raw_response)
                raise SurePetcareError()

            return token

        except asyncio.TimeoutError as error:
            logger.debug("Timeout while calling %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareConnectionError() from error
        except (aiohttp.ClientError, AttributeError) as error:
            logger.debug("Failed to fetch %s: %s", AUTH_RESOURCE, error)
            raise SurePetcareError() from error
        finally:
            if not self._session:
                await session.close()

    async def call(
        self,
        method: str,
        resource: str,
        data: dict[str, Any] | None = None,
        second_try: bool = False,
        **_: Any,
    ) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""

        # logger.debug("")
        # logger.debug("🐾 %s call to: %s", method, resource)
        # if data:
        #     logger.debug("🐾   with data: %s", data)

        if not self._auth_token:
            self._auth_token = await self.get_token()

        if method not in ["GET", "PUT", "POST"]:
            raise HTTPException(f"unknown http method: {method}")

        response_data = None

        session = self._session if self._session else aiohttp.ClientSession()

        try:
            with async_timeout.timeout(self._api_timeout):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    # logger.debug("🐾 \x1b[38;2;255;26;102m·\x1b[0m etag: %s", headers[ETAG])

                await session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await session.request(
                    method, resource, headers=headers, data=data
                )

                if response.status == HTTPStatus.OK or response.status == HTTPStatus.CREATED:

                    self.resources[resource] = response_data = await response.json()

                    if ETAG in response.headers:
                        self._etags[resource] = response.headers[ETAG].strip('"')

                elif response.status == HTTPStatus.NOT_MODIFIED:
                    # Etag header matched, no new data available
                    logger.debug(
                        "🐾 \x1b[38;2;0;255;0m·\x1b[0m %d: etag matched - no new data available",
                        response.status,
                    )

                elif response.status == HTTPStatus.UNAUTHORIZED:
                    logger.error(
                        "🐾 \x1b[38;2;255;26;102m·\x1b[0m %s %s: %d | %s",
                        method,
                        resource.replace("https://", ""),
                        response.status,
                        response,
                    )
                    self._auth_token = None
                    if not second_try:
                        token_refreshed = self.get_token()
                        if token_refreshed:
                            await self.call(method="GET", resource=resource, second_try=True)

                    raise SurePetcareAuthenticationError()

                else:
                    logger.info(
                        "🐾 \x1b[38;2;255;0;255m·\x1b[0m %s %s: %d | %s",
                        method,
                        resource.replace("https://", ""),
                        response.status,
                        response,
                    )

                if response_data:
                    responselen = len(response_data.get("data", 0))
                else:
                    responselen = 0
                logger.debug(
                    "🐾 \x1b[38;2;0;255;0m·\x1b[0m %s %s | %d",
                    method,
                    resource.replace("https://", ""),
                    responselen,
                )

                return response_data

        except (asyncio.TimeoutError, aiohttp.ClientError) as error:
            logger.error("Can not load data from %s", resource)
            raise SurePetcareConnectionError() from error
        finally:
            if not self._session:
                await session.close()

    async def get_pets(self) -> list[dict[str, Any]] | None:
        """Retrieve the pet data/state."""
        resource = PET_RESOURCE

        response_data: list[dict[str, Any]] | None = []

        response: dict[str, Any] | None = await self.call(method="GET", resource=resource)
        if response:
            response_data = response.get("data")

        return response_data

    async def set_pet_location(self, pet_id: int, location: Location) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        resource = POSITION_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, pet_id=pet_id)
        data = {
            "where": int(location.value),
            "since": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if (response := await self.call(method="POST", resource=resource, data=data)) and (
            response_data := response.get("data")
        ):

            desired_state = data.get("where")
            state = response_data.get("where")

            # check if the state is correctly updated
            if state == desired_state:
                return response

        raise SurePetcareError(f"Setting position of {pet_id} failed!")

    async def lock(self, device_id: int) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        return await self._set_lock_state(device_id, LockState.LOCKED_ALL)

    async def lock_in(self, device_id: int) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        return await self._set_lock_state(device_id, LockState.LOCKED_IN)

    async def lock_out(self, device_id: int) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        return await self._set_lock_state(device_id, LockState.LOCKED_OUT)

    async def unlock(self, device_id: int) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        return await self._set_lock_state(device_id, LockState.UNLOCKED)

    async def _set_lock_state(self, device_id: int, mode: LockState) -> dict[str, Any] | None:
        """Retrieve the flap data/state."""
        resource = CONTROL_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, device_id=device_id)
        data = {"locking": int(mode.value)}

        if (
            response := await self.call(
                method="PUT", resource=resource, device_id=device_id, data=data
            )
        ) and (response_data := response.get("data")):

            desired_state = data.get("locking")
            state = response_data.get("locking")

            # check if the state is correctly updated
            if state == desired_state:
                return response

        # return None
        raise SurePetcareError("ERROR (UN)LOCKING DEVICE - PLEASE CHECK IMMEDIATELY!")
