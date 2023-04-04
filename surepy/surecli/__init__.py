"""
surepy.cli
====================================
The cli module of surepy

|license-info|
"""

from __future__ import annotations

import asyncio
import json

from datetime import datetime
from functools import wraps
from pathlib import Path
from shutil import copyfile
from sys import exit
from typing import Any, cast

import click

from aiohttp import ClientSession, TCPConnector
from rich import box
from rich.table import Table

from surepy import Surepy, __name__ as sp_name, __version__ as sp_version, console, natural_time
from surepy.entities.devices import Flap, SurepyDevice, Feeder
from surepy.entities.pet import Pet
from surepy.enums import Location, LockState


TOKEN_ENV = "SUREPY_TOKEN"


def coro(f: Any) -> Any:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


token_file = Path("~/.surepy.token").expanduser()
old_token_file = token_file.with_suffix(".old_token")

CONTEXT_SETTINGS: dict[str, Any] = dict(help_option_names=["--help"])

version_message = (
    f" [#ffffff]{sp_name}[/] 🐾 [#666666]v[#aaaaaa]{sp_version.replace('.', '[#ff1d5e].[/]')}"
)


def print_header() -> None:
    """print header to terminal"""
    print()
    console.print(version_message, justify="left")
    print()


def token_available(ctx: click.Context) -> str | None:
    if token := ctx.obj.get("token"):
        return str(token)

    console.print("\n  [red bold]no token found![/]\n  checked in:\n")
    console.print("    · [bold]--token[/]")
    console.print(f"    · [bold]{TOKEN_ENV}[/] env var")
    console.print(f"    · [white bold]{token_file}[/]")
    console.print("\n\n  sorry 🐾 [bold]¯\\_(ツ)_/¯[/]\n\n")
    return None


# async def json_response(
#     data: dict[str, Any], ctx: click.Context, sp: Surepy | None = None
# ) -> None:
#     if ctx.obj.get("json", False):
#         if sp:
#             await sp.sac.close_session()
#
#         console.print(data)
#
#         exit(0)
#


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
@click.option("--version", default=False, is_flag=True, help=f"show {sp_name} version")
# @click.option("-v", "--verbose", default=False, is_flag=True, help="enable additional output")
# @click.option("-d", "--debug", default=False, is_flag=True, help="enable debug output")
@click.option("-j", "--json", default=False, is_flag=True, help="enable json api response output")
@click.option(
    "-t", "--token", "user_token", default=None, type=str, help="api token", hide_input=True
)
def cli(ctx: click.Context, json: bool, user_token: str, version: bool) -> None:
    """surepy cli 🐾

    https://github.com/benleb/surepy
    """

    ctx.ensure_object(dict)
    # ctx.obj["verbose"] = verbose
    # ctx.obj["debug"] = debug
    ctx.obj["json"] = json
    ctx.obj["token"] = user_token

    # if not json:
    #     print_header()

    if not ctx.invoked_subcommand:

        if version:
            click.echo(version_message)
            exit(0)

        click.echo(ctx.get_help())


@cli.command()
@click.pass_context
@click.option(
    "-u", "--user", required=True, type=str, help="sure petcare api account username (email)"
)
@click.option(
    "-p",
    "--password",
    required=True,
    type=str,
    help="sure petcare api account password",
    hide_input=True,
)
@coro
async def token(ctx: click.Context, user: str, password: str) -> None:
    """get a token"""

    surepy_token: str | None = None

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        sp = Surepy(email=user, password=password, session=session)

        if surepy_token := await sp.sac.get_token():

            if token_file.exists() and surepy_token != token_file.read_text(encoding="utf-8"):
                copyfile(token_file, old_token_file)

            token_file.write_text(surepy_token, encoding="utf-8")

        # await sp.sac.close_session()

    console.rule(f"[bold]{user}[/] [#ff1d5e]·[/] [bold]Token[/]", style="#ff1d5e")
    console.print(f"[bold]{token}[/]", soft_wrap=True)
    console.rule(style="#ff1d5e")
    print()


@cli.command()
@click.pass_context
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def pets(ctx: click.Context, token: str | None) -> None:
    """get pets"""

    token = token if token else ctx.obj.get("token", None)

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        sp = Surepy(auth_token=token, session=session)

        pets: list[Pet] = await sp.get_pets()

        # json output
        if ctx.obj.get("json", False):
            for pet in pets:
                json_str = json.dumps(pet.raw_data(), indent=4)
                print(json_str)
            return

        # pretty print
        table = Table(box=box.MINIMAL)
        table.add_column("Name", style="bold")
        table.add_column("Where", justify="right")
        table.add_column("Feeding A", justify="right", style="bold")
        table.add_column("Feeding B", justify="right", style="bold")
        table.add_column("Lunch Time", justify="right", style="bold")
        table.add_column("Drinking", justify="right", style="bold")
        table.add_column("Drink Time", justify="right", style="bold")
        table.add_column("ID 👤 ", justify="right")
        table.add_column("Household 🏡", justify="right")

        for pet in pets:

            feeding_a = feeding_b = lunch_time = None
            drinking_change = drink_time = None

            if pet.feeding:
                feeding_a = f"{pet.feeding.change[0]}g"
                feeding_b = f"{pet.feeding.change[1]}g"
                lunch_time = pet.feeding.at.time() if pet.feeding.at else None
            if pet.drinking:
                drinking_change = f"{pet.drinking.change[0]}ml"
                drink_time = pet.drinking.at.time() if pet.drinking.at else None

            table.add_row(
                str(pet.name),
                str(pet.location),
                f"{feeding_a}",
                f"{feeding_b}",
                str(lunch_time),
                f"{drinking_change}",
                str(drink_time),
                str(pet.pet_id),
                str(pet.household_id),
            )

        console.print(table, "", sep="\n")


@cli.command()
@click.pass_context
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def devices(ctx: click.Context, token: str | None) -> None:
    """get devices"""

    token = token if token else ctx.obj.get("token", None)

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        sp = Surepy(auth_token=token, session=session)

        devices: list[SurepyDevice] = await sp.get_devices()

        # await json_response(devices, ctx)

        # table = Table(title="[bold][#ff1d5e]·[/] Devices [#ff1d5e]·[/]", box=box.MINIMAL)
        table = Table(box=box.MINIMAL)
        table.add_column("ID", justify="right", style="")
        table.add_column("Household", justify="right", style="")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="")
        table.add_column("Serial", style="")

        # sorted_devices = sorted(devices, key=lambda x: int(devices[x]["household_id"]))

        # devices = await sp.sac.get_devices()
        # devices = await sp.get_entities()

        for device in devices:

            table.add_row(
                str(device.id),
                str(device.household_id),
                str(device.name),
                str(device.type.name.replace("_", " ").title()),
                str(device.serial) or "-",
            )

        console.print(table, "", sep="\n")


@cli.command()
@click.pass_context
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@click.option("-p", "--pet", "pet_id", required=False, type=int, help="id of the pet")
@click.option(
    "-h", "--household", "household_id", required=True, type=int, help="id of the household"
)
@coro
async def report(
    ctx: click.Context, household_id: int, pet_id: int | None = None, token: str | None = None
) -> None:
    """get pet/household report"""

    token = token if token else ctx.obj.get("token", None)

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        sp = Surepy(auth_token=token, session=session)

        entities = await sp.get_entities()

        json_data = await sp.get_report(pet_id=pet_id, household_id=household_id)

        if data := json_data.get("data"):

            table = Table(box=box.MINIMAL)

            all_keys: list[str] = ["pet", "from", "to", "duration", "entry_device", "exit_device"]

            for key in all_keys:
                table.add_column(str(key))

            for pet in data:

                datapoints_drinking: list[dict[str, Any]] = pet.get("drinking", {}).get(
                    "datapoints", []
                )
                datapoints_feeding: list[dict[str, Any]] = pet.get("feeding", {}).get(
                    "datapoints", []
                )
                datapoints_movement: list[dict[str, Any]] = pet.get("movement", {}).get(
                    "datapoints", []
                )

                datapoints = datapoints_drinking + datapoints_feeding + datapoints_movement

                if datapoints:

                    for datapoint in datapoints:

                        from_time = datetime.fromisoformat(datapoint["from"])
                        to_time = (
                            datetime.fromisoformat(datapoint["to"])
                            if "active" not in datapoint
                            else None
                        )

                        if "active" in datapoint:
                            datapoint["duration"] = (
                                datetime.now(tz=from_time.tzinfo) - from_time
                            ).total_seconds()

                        entry_device = entities.get(datapoint.get("entry_device_id", 0), None)
                        exit_device = entities.pop(datapoint.get("exit_device_id", 0), None)

                        table.add_row(
                            str(entities[pet["pet_id"]].name),
                            str(from_time.strftime("%d/%m %H:%M")),
                            str(to_time.strftime("%d/%m %H:%M") if to_time else "-"),
                            str(natural_time(datapoint["duration"])),
                            str(entry_device.name if entry_device else "-"),
                            str(exit_device.name if exit_device else "-"),
                        )

            console.print(table, "", sep="\n")


@cli.command()
@click.pass_context
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def notification(ctx: click.Context, token: str | None = None) -> None:
    """get notifications"""

    token = token if token else ctx.obj.get("token", None)

    async with ClientSession(connector=TCPConnector(ssl=False)) as session:
        sp = Surepy(auth_token=token, session=session)

        json_data = await sp.get_notification() or None

        if json_data and (data := json_data.get("data")):

            table = Table(box=box.MINIMAL)

            all_keys: set[str] = set()
            all_keys.update(*[entry.keys() for entry in data])

            for key in all_keys:
                table.add_column(str(key))

            for entry in data:
                table.add_row(*([str(e) for e in entry.values()]))

            console.print(table, "", sep="\n")


@cli.command()
@click.pass_context
@click.option(
    "-d", "--device", "device_id", required=True, type=int, help="id of the sure petcare device"
)
@click.option(
    "-m",
    "--mode",
    required=True,
    type=click.Choice(["lock", "in", "out", "unlock"]),
    help="locking mode",
)
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def locking(ctx: click.Context, device_id: int, mode: str, token: str | None = None) -> None:
    """lock control"""

    token = token if token else ctx.obj.get("token", None)

    sp = Surepy(auth_token=str(token))

    if (flap := await sp.get_device(device_id=device_id)) and (type(flap) == Flap):

        flap = cast(Flap, flap)

        lock_state: LockState

        if mode == "lock":
            lock_state = LockState.LOCKED_ALL
            state = "locked"
        elif mode == "in":
            lock_state = LockState.LOCKED_IN
            state = "locked in"
        elif mode == "out":
            lock_state = LockState.LOCKED_OUT
            state = "locked out"
        elif mode == "unlock":
            lock_state = LockState.UNLOCKED
            state = "unlocked"
        else:
            return

        console.print(f"setting {flap.name} to '{state}'...")

        if await sp.sac._set_lock_state(device_id=device_id, mode=lock_state) and (
            device := await sp.get_device(device_id=device_id)
        ):
            console.print(f"✅ {device.name} set to '{state}' 🐾")
        else:
            console.print(f"❌ setting to '{state}' may have worked but something is fishy..!")

        # await sp.sac.close_session()


@cli.command()
@click.pass_context
@click.option("--pet", "pet_id", required=True, type=int, help="id of the pet")
@click.option(
    "--position",
    required=True,
    type=click.Choice(["in", "out"]),
    help="position",
)
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def position(
    ctx: click.Context, pet_id: int, position: str, token: str | None = None
) -> None:
    """set pet position"""

    token = token if token else ctx.obj.get("token", None)

    sp = Surepy(auth_token=str(token))

    pet: Pet | None
    location: Location | None

    if (pet := await sp.get_pet(pet_id=pet_id)) and (type(pet) == Pet):

        if position == "in":
            location = Location.INSIDE
        elif position == "out":
            location = Location.OUTSIDE
        else:
            return

        if location:
            if await sp.sac.set_pet_location(pet.id, location):
                console.print(f"{pet.name} set to '{location.name}' 🐾")
            else:
                console.print(
                    f"setting to '{location.name}' probably worked but something else is fishy...!"
                )

        # await sp.sac.close_session()

@cli.command()
@click.pass_context
@click.option(
    "-d", "--device", "device_id", required=True, type=int, help="id of the sure petcare device"
)
@click.option("-p", "--pet", "pet_id", required=False, type=int, help="id of the pet")
@click.option(
    "-m",
    "--mode",
    required=True,
    type=click.Choice(["add", "remove", "list"]),
    help="assignment action",
)
@click.option(
    "-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True
)
@coro
async def feederassign(ctx: click.Context, device_id: int, mode: str, pet_id: int | None = None, token: str | None = None) -> None:
    """feeder pet assignment"""

    token = token if token else ctx.obj.get("token", None)

    sp = Surepy(auth_token=str(token))

    if (feeder := await sp.get_device(device_id=device_id)) and (type(feeder) == Feeder):

        pets: list[Pet] = await sp.get_pets()

        if mode == "list":
            table = Table(box=box.MINIMAL)
            table.add_column("ID", style="bold")
            table.add_column("Name", style="")
            table.add_column("Created At", style="")
            for tag in feeder.tags.values():
                for pet in pets:
                    if tag.id == pet.tag_id:
                        table.add_row(
                            str(pet.id),
                            str(pet.name),
                            str(datetime.fromisoformat(tag.created_at())),
                        )
            console.print(table, "", sep="\n")
        if mode == "add":
            for pet in pets:
                if pet.id == pet_id:
                    for tag in feeder.tags.values():
                        if tag.id == pet.tag_id:
                            console.print(f"Pet is already assigned to this feeder.")
                            return
                    if await sp.sac._add_tag_to_device(device_id=device_id, tag_id=pet.tag_id):
                        console.print(f"✅ {pet.name} added to '{feeder.name}' 🐾")
        if mode == "remove":
            for pet in pets:
                if pet.id == pet_id:
                    for tag in feeder.tags.values():
                        if tag.id == pet.tag_id:
                            if await sp.sac._remove_tag_from_device(device_id=device_id, tag_id=pet.tag_id):
                                console.print(f"✅ {pet.name} removed from '{feeder.name}' 🐾")
                                return
                    console.print("Pet is not assigned to this feeder.")
        else:
            return
        # await sp.sac.close_session()

if __name__ == "__main__":
    cli(obj={})
