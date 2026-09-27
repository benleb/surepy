"""Offline tests for cursor-based household timeline reads."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from surepy import Surepy
from surepy.const import BASE_RESOURCE
from surepy.exceptions import SurePetcareAuthenticationError, SurePetcareError


@pytest.fixture
def client() -> Surepy:
    return Surepy(auth_token="x" * 321, session=MagicMock())


@pytest.mark.asyncio
@pytest.mark.parametrize("before_id", [None, 123])
async def test_page_preserves_events(client: Surepy, before_id: int | None) -> None:
    events = [{"id": 100 - i, "type": 987, "created_at": "2026-09-26T21:59:00Z"} for i in range(25)]
    client.sac.call = AsyncMock(return_value={"data": events})

    assert await client.get_household_timeline_page(42, before_id=before_id) == events
    resource = f"{BASE_RESOURCE}/timeline/household/42?page_size=25"
    if before_id is not None:
        resource += f"&before_id={before_id}"
    client.sac.call.assert_awaited_once_with(method="GET", resource=resource, raise_on_error=True)


@pytest.mark.asyncio
async def test_empty_page(client: Surepy) -> None:
    client.sac.call = AsyncMock(return_value={"data": []})
    assert await client.get_household_timeline_page(42) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [304, 500, 429])
async def test_http_cache_and_errors(client: Surepy, status: int) -> None:
    resource = f"{BASE_RESOURCE}/timeline/household/42?page_size=25"
    client.sac.resources[resource] = {"data": [{"id": 1}]}
    response = MagicMock(status=status)
    client.sac._session.options = AsyncMock()
    client.sac._session.request = AsyncMock(return_value=response)

    if status == 304:
        assert await client.get_household_timeline_page(42) == [{"id": 1}]
    else:
        with pytest.raises(SurePetcareError, match=f"Unexpected HTTP status: {status}"):
            await client.get_household_timeline_page(42)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, {}, {"data": None}, {"data": [{}]}])
async def test_invalid_page_raises(client: Surepy, response: dict | None) -> None:
    client.sac.call = AsyncMock(return_value=response)
    with pytest.raises(SurePetcareError, match="[Ii]nvalid"):
        await client.get_household_timeline_page(42)


@pytest.mark.asyncio
async def test_authentication_error_propagates(client: Surepy) -> None:
    client.sac.call = AsyncMock(side_effect=SurePetcareAuthenticationError)
    with pytest.raises(SurePetcareAuthenticationError):
        await client.get_household_timeline_page(42)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"data": None}, [{"id": 1}], {"data": 123}])
async def test_malformed_http_response(client: Surepy, body: object) -> None:
    response = MagicMock(status=200, headers={})
    response.json = AsyncMock(return_value=body)
    client.sac._session.options = AsyncMock()
    client.sac._session.request = AsyncMock(return_value=response)
    with pytest.raises(SurePetcareError, match="[Ii]nvalid"):
        await client.get_household_timeline_page(42)


@pytest.mark.asyncio
async def test_legacy_method_is_unchanged(client: Surepy) -> None:
    client.sac.call = AsyncMock(return_value={"data": [{"id": 1}]})
    assert await client.get_household_timeline(42) == [{"id": 1}]
    client.sac.call.assert_awaited_once_with(
        method="GET", resource=f"{BASE_RESOURCE}/timeline/household/42?page=1"
    )
