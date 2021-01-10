"""
surepy
====================================
The core module of surepy

|license-info|
"""

import asyncio
import logging

from http import HTTPStatus
from http.client import HTTPException
from logging import Logger
from os import environ
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid1

import aiohttp
import async_timeout
import requests

from surepy.const import (
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
    ETAG,
    HOST,
    HTTP_HEADER_X_REQUESTED_WITH,
    ORIGIN,
    PET_RESOURCE,
    REFERER,
    SUREPY_USER_AGENT,
    USER_AGENT,
)
from surepy.exceptions import (
    SurePetcareAuthenticationError,
    SurePetcareConnectionError,
    SurePetcareError,
)


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


class SureAPIClient:
    """Communication with the Sure Petcare API."""

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        # loop: Optional[asyncio.AbstractEventLoop] = None,
        session: Optional[aiohttp.ClientSession] = None,
        auth_token: Optional[str] = None,
        api_timeout: int = API_TIMEOUT,
    ) -> None:
        """Initialize the connection to the Sure Petcare API."""
        # self._loop = loop or asyncio.get_event_loop()
        self._session = session or aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False)
        )
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
        elif token := find_token():
            self._auth_token = token
        else:
            # no valid credentials/token
            SurePetcareAuthenticationError("sorry 🐾 no valid credentials/token found ¯\\_(ツ)_/¯")

        # storage for received api data
        self.resources: Dict[str, Any] = {}
        # storage for etags
        self._etags: Dict[str, str] = {}

        logger.debug("initialization completed | vars(): %s", vars())

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
            USER_AGENT: SUREPY_USER_AGENT,
            REFERER: "https://surepetcare.io",
            ACCEPT_ENCODING: "gzip, deflate",
            ACCEPT_LANGUAGE: "en-US,en-GB;q=0.9",
            HTTP_HEADER_X_REQUESTED_WITH: "com.sureflap.surepetcare",
            AUTHORIZATION: f"Bearer {self._auth_token}",
            "X-Device-Id": self._device_id,
        }

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

            if raw_response.status_code == HTTPStatus.OK:

                response: Dict[str, Any] = raw_response.json()

                if "data" in response and "token" in response["data"]:
                    token = self._auth_token = response["data"]["token"]

            elif raw_response.status_code == HTTPStatus.NOT_MODIFIED:
                # Etag header matched, no new data available
                pass

            elif raw_response.status_code == HTTPStatus.UNAUTHORIZED:
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

    async def call(
        self,
        method: str,
        resource: str,
        data: Optional[Dict[str, Any]] = None,
        second_try: bool = False,
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""

        logger.debug("self._auth_token: %s", self._auth_token)
        if not self._auth_token:
            self._auth_token = self.get_token()

        if method not in ["GET", "PUT", "POST"]:
            raise HTTPException("unknown http method: %d", str(method))

        response_data: Dict[str, Any] = {}

        try:
            with async_timeout.timeout(self._api_timeout):  # , loop=self._loop):
                headers = self._generate_headers()

                # use etag if available
                if resource in self._etags:
                    headers[ETAG] = str(self._etags.get(resource))
                    logger.debug("using available etag '%s' in headers: %s", ETAG, headers)

                logger.debug("headers: %s", headers)

                await self._session.options(resource, headers=headers)
                response: aiohttp.ClientResponse = await self._session.request(
                    method, resource, headers=headers, data=data
                )

                logger.debug("response.status: %d", response.status)

            if response.status == HTTPStatus.OK or response.status == HTTPStatus.CREATED:

                self.resources[resource] = response_data = await response.json()

                if ETAG in response.headers:
                    self._etags[resource] = response.headers[ETAG].strip('"')

            elif response.status == HTTPStatus.NOT_MODIFIED:
                # Etag header matched, no new data available
                pass

            elif response.status == HTTPStatus.UNAUTHORIZED:
                logger.debug("AuthenticationError! Try: %s: %s", second_try, response)
                self._auth_token = None
                if not second_try:
                    token_refreshed = self.get_token()
                    if token_refreshed:
                        await self.call(method="GET", resource=resource, second_try=True)

                raise SurePetcareAuthenticationError()

            else:
                logger.info("Response from %s:\n%s", resource, response)

            return response_data

        except (asyncio.TimeoutError, aiohttp.ClientError):
            logger.error("Can not load data from %s", resource)
            raise SurePetcareConnectionError()

    async def get_pet(self, pet_id: int) -> Optional[List[Dict[str, Any]]]:
        """Retrieve the pet data/state."""
        resource = PET_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, pet_id=pet_id)

        response_data: Optional[List[Dict[str, Any]]] = []

        if response := await self.call(method="GET", resource=resource):
            response_data = response.get("data")

        return response_data
