"""Offline tests for the token handling of the API client."""

import logging

from http import HTTPStatus
from typing import Any

import pytest

from surepy import MESTART_RESOURCE, Surepy
from surepy.const import AUTH_RESOURCE
from surepy.exceptions import SurePetcareAuthenticationError

STALE_TOKEN = "s" * 400
FRESH_TOKEN = "f" * 400


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, Any] | None = None) -> None:
        self.status = status
        self.headers: dict[str, str] = {}
        self._payload = payload

    async def json(self) -> dict[str, Any] | None:
        return self._payload

    def release(self) -> None:
        pass


class FakeSession:
    """Answers 401 for every token except the ones listed as valid."""

    def __init__(self, valid_tokens: set[str], issued_token: str | None = FRESH_TOKEN) -> None:
        self.valid_tokens = valid_tokens
        self.issued_token = issued_token

    async def options(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def request(
        self, method: str, resource: str, headers: dict[str, str], **kwargs: Any
    ) -> FakeResponse:
        token = headers["Authorization"].removeprefix("Bearer ")
        if token in self.valid_tokens:
            return FakeResponse(HTTPStatus.OK, {"data": {"pets": []}})
        return FakeResponse(HTTPStatus.UNAUTHORIZED)

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        assert url == AUTH_RESOURCE
        if self.issued_token is None:
            return FakeResponse(HTTPStatus.UNAUTHORIZED)
        return FakeResponse(HTTPStatus.OK, {"data": {"token": self.issued_token}})


def _surepy(session: FakeSession) -> Surepy:
    return Surepy(
        email="user@example.com",
        password="secret",
        auth_token=STALE_TOKEN,
        session=session,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_auth_token_reflects_refreshed_token(caplog: pytest.LogCaptureFixture) -> None:
    spy = _surepy(FakeSession(valid_tokens={FRESH_TOKEN}))
    assert spy.auth_token == STALE_TOKEN

    with caplog.at_level(logging.INFO, logger="surepy.client"):
        response = await spy.sac.call(method="GET", resource=MESTART_RESOURCE)

    assert response == {"data": {"pets": []}}
    assert spy.auth_token == FRESH_TOKEN
    assert spy.sac.auth_token == FRESH_TOKEN
    # the expected 401 with the stale token is not reported as an error
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.asyncio
async def test_401_with_fresh_token_is_logged_as_error(caplog: pytest.LogCaptureFixture) -> None:
    spy = _surepy(FakeSession(valid_tokens=set()))

    with caplog.at_level(logging.INFO, logger="surepy.client"):
        with pytest.raises(SurePetcareAuthenticationError):
            await spy.sac.call(method="GET", resource=MESTART_RESOURCE)

    assert [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.asyncio
async def test_invalid_credentials_raise() -> None:
    spy = _surepy(FakeSession(valid_tokens=set(), issued_token=None))

    with pytest.raises(SurePetcareAuthenticationError):
        await spy.sac.call(method="GET", resource=MESTART_RESOURCE)

    assert spy.auth_token is None
