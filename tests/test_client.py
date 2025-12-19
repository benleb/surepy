from pathlib import Path
import pytest
import pprint
from shutil import copyfile
from datetime import datetime, timedelta
import configparser

from surepy import Surepy

token_file = Path("~/.surepy.token").expanduser()
old_token_file = token_file.with_suffix(".old_token")
auth_file = Path("~/.surepy.auth").expanduser()
config = configparser.ConfigParser()
config.read(str(auth_file))


def file_older_then(file: Path, delta: timedelta) -> bool:
    return datetime.fromtimestamp(file.stat().st_mtime) < (datetime.now() - delta)


async def get_surepy() -> Surepy | None:
    if not token_file.exists() or file_older_then(token_file, timedelta(minutes=5)):

        spy = Surepy(
            email=config.get("Login", "email"),
            password=config.get("Login", "password"),
        )

        if surepy_token := await spy.sac.get_token():

            if token_file.exists() and surepy_token != token_file.read_text(encoding="utf-8"):
                copyfile(token_file, old_token_file)

            token_file.write_text(surepy_token, encoding="utf-8")

        return spy
    else:
        return Surepy(auth_token=token_file.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_get_entities() -> None:
    spy = await get_surepy()

    response = await spy.get_entities(refresh=True)

    with open("response.txt", "w") as file:
        file.write(pprint.pformat(response))

    assert len(response) > 0


@pytest.mark.asyncio
async def test_get_actions() -> None:
    spy = await get_surepy()

    response = await spy.get_actions(household_id=config.get("IDs", "household"))

    assert len(response) > 0


@pytest.mark.asyncio
async def test_get_latest_anonymous_drinks() -> None:
    spy = await get_surepy()

    response = await spy.get_latest_anonymous_drinks(household_id=config.get("IDs", "household"))

    assert len(response) > 0
