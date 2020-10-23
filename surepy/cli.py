#!/usr/bin/env python3

import asyncio

from datetime import datetime
from functools import wraps
from os import environ
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

import click

from halo import Halo
from rich import box, print
from rich.console import Console
from rich.table import Table

from . import (
    ENV_SUREPY_TOKEN,
    SureLocationID,
    SurePetcare,
    SurePetcareAuthenticationError,
    SureProductID,
    __name__ as sp_name,
    __version__ as sp_version,
    natural_time,
)


def coro(f: Callable) -> Callable:  # type: ignore
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


surepy_token_file = Path("~/.surepy.token").expanduser()

console = Console(width=100)


CONTEXT_SETTINGS = dict(help_option_names=["--help"])

version_message = (
    f" 🐾 [#ffffff][bold]{sp_name}[/bold] [#ff1d5e]·[/] [#666666]v[#aaaaaa]{sp_version}"
    # f" 🐾 [#ffffff][bold]{sp_name}[/bold] [#ff1d5e]·[/] {sp_version.replace('.', '[#ff1d5e].[/]')}"
    # f"[#ff1d5e link=https://github.com/benleb/surepy]github.com/benleb/surepy[/]"
    # f"[link=https://twitter.com/ben_leb]@ben_leb[/link][/]"
)


def print_header() -> None:
    print()
    console.print(version_message, justify="left")
    print()


def find_token(token: Optional[str]) -> Optional[str]:
    def seems_valid(token: str) -> bool:
        return token is not None and token.isascii() and token.isprintable() and (320 < len(token) < 384)

    # check parameter token
    if token and seems_valid(token=token):
        return token

    # check env token
    elif (env_token := environ.get(ENV_SUREPY_TOKEN, None)) and seems_valid(token=env_token):
        return env_token

    # check file token
    elif (
        surepy_token_file.exists()
        and (file_token := surepy_token_file.read_text(encoding="utf-8"))
        and seems_valid(token=file_token)
    ):
        return file_token

    else:
        print(" 🐾 wtf?! [bold]¯\\_(ツ)_/¯[/]")
        raise SurePetcareAuthenticationError


def token_available(ctx: click.Context) -> Optional[str]:
    if token := ctx.obj.get("token"):
        return str(token)

    console.print("\n  [red bold]no token found![/]\n  checked in:\n")
    console.print("    · [bold]--token[/]")
    console.print(f"    · [bold]{ENV_SUREPY_TOKEN}[/] env var")
    console.print(f"    · [white bold]{surepy_token_file}[/]")
    console.print("\n\n  sorry 🐾 [bold]¯\\_(ツ)_/¯[/]\n\n")
    return None


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
@click.option("--version", default=False, is_flag=True, help=f"show {sp_name} version")
# @click.option("-v", "--verbose", default=False, is_flag=True, help="enable additional output")
# @click.option("-d", "--debug", default=False, is_flag=True, help="enable debug output")
@click.option("-t", "--token", "user_token", required=False, type=str, help="sure petcare api token", hide_input=True)
def cli(ctx: click.Context, user_token: str, version: bool, verbose: bool, debug: bool) -> None:
    """surepy cli 🐾

    https://github.com/benleb/surepy
    """

    print_header()

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["token"] = find_token(user_token)

    if not ctx.invoked_subcommand:

        if version:
            click.echo(version_message)
            exit(0)

        click.echo(ctx.get_help())


@cli.command()
@click.pass_context
@click.option("-u", "--user", required=True, type=str, help="sure petcare api account username (email)")
@click.option("-p", "--password", required=True, type=str, help="sure petcare api account password", hide_input=True)
@coro
async def token(ctx: click.Context, user: str, password: str) -> None:
    """get a token"""

    token: Optional[str] = None

    with Halo(text="fetching token", spinner="dots", color="magenta") as spinner:
        sp = SurePetcare(email=user, password=password)

        if not sp._auth_token:
            token = await sp._refresh_token()
            await sp._session.close()

        # spinner.succeed(f"{sp._auth_token}")
        spinner.succeed("token received!")

    if not surepy_token_file.exists() and token:
        surepy_token_file.write_text(token, encoding="utf-8")

    console.rule(f"[bold]{user}[/] [#ff1d5e]·[/] [bold]Token[/]", style="#ff1d5e")
    console.print(f"[bold]{sp._auth_token}[/]", soft_wrap=True)
    console.rule(style="#ff1d5e")
    print()


@cli.command()
@click.pass_context
@click.option("-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True)
@coro
async def pets(ctx: click.Context, token: Optional[str]) -> None:
    """get pets"""

    if token := ctx.obj.get("token", find_token(token)):

        sp = SurePetcare(auth_token=str(token))
        pets = await sp.pets

        table = Table(box=box.MINIMAL)
        table.add_column("Name 🐾", style="bold")
        table.add_column("Where 🥾", justify="right")
        table.add_column("🍽  ⚖️  a", justify="right", style="bold")
        table.add_column("🍽  ⚖️  b", justify="right", style="bold")
        table.add_column("🍽  lunched time", justify="right")
        table.add_column("ID 👤 ", justify="right")
        table.add_column("Household 🏡", justify="right")

        sorted_pets = sorted(pets, key=lambda x: int(pets[x]["household_id"]))

        for pet_id in sorted_pets:
            pet: Dict[str, Any] = pets[pet_id]

            where = (
                "unknown"
                if "position" not in pet or "where" not in pet["position"]
                else SureLocationID(pet["position"]["where"]).name.capitalize()
            )

            if (status := pet.get("status")) and (feeding := status.get("feeding")):
                change_a, change_b = feeding["change"]
                change_a = f"{change_a}g"
                change_b = f"{change_b}g"
                ate_at = feeding["at"]
                lunch_time = str(datetime.fromisoformat(ate_at).strftime("%d/%m %H:%M"))
            else:
                change_a = change_b = lunch_time = ""

            table.add_row(
                str(pet["name"]),
                str(where),
                f"{change_a}",
                f"{change_b}",
                str(lunch_time),
                str(pet["id"]),
                str(pet["household_id"]),
            )

        console.print(table, "", sep="\n")

        await sp._session.close()


@cli.command()
@click.pass_context
@click.option("-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True)
@coro
async def devices(ctx: click.Context, token: Optional[str]) -> None:
    """get devices"""

    if token := ctx.obj.get("token", find_token(token)):

        sp = SurePetcare(auth_token=str(token))
        devices = await sp.devices

        table = Table(title="[bold][#ff1d5e]·[/] Devices [#ff1d5e]·[/]", box=box.MINIMAL)
        table.add_column("ID", justify="right", style="")
        table.add_column("Household", justify="right", style="")
        table.add_column("Type", style="")
        table.add_column("Name", style="bold")
        table.add_column("Serial", justify="right", style="")

        sorted_devices = sorted(devices, key=lambda x: int(devices[x]["household_id"]))

        for device_id in sorted_devices:
            device: Dict[str, Any] = devices[device_id]
            table.add_row(
                str(device["id"]),
                str(device["household_id"]),
                str(SureProductID(device["product_id"]).name.replace("_", " ").title()),
                str(device.get("name", "unknown")),
                str(device.get("serial_number", "-")),
            )

        console.print(table, "", sep="\n")

        await sp._session.close()


@cli.command()
@click.pass_context
@click.option("-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True)
@click.option("-p", "--pet", "pet_id", required=False, type=int, help="id of the pet")
@click.option("-h", "--household", "household_id", required=True, type=int, help="id of the household")
@coro
async def report(
    ctx: click.Context, household_id: int, pet_id: Optional[int] = None, token: Optional[str] = None
) -> None:
    """get pet/household report"""

    if token := ctx.obj.get("token", find_token(token)):

        sp = SurePetcare(auth_token=str(token))

        if data := (await sp.get_report(pet_id=pet_id, household_id=household_id)).get("data"):

            table = Table(box=box.MINIMAL)

            all_keys: List[str] = ["pet", "from", "to", "duration", "entry_device_id", "exit_device_id"]

            for key in all_keys:
                table.add_column(str(key))

            for pet in data:

                if (movement := pet["movement"]) and (datapoints := movement["datapoints"]):

                    for datapoint in datapoints[-25:]:

                        if "active" in datapoint:
                            continue

                        table.add_row(
                            str((await sp.pet(pet["pet_id"])).get("name")),
                            str(str(datetime.fromisoformat(datapoint["from"]).strftime("%d/%m %H:%M"))),
                            str(str(datetime.fromisoformat(datapoint["to"]).strftime("%d/%m %H:%M"))),
                            str(natural_time(datapoint["duration"])),
                            str((await sp.device(datapoint["entry_device_id"])).get("name")),
                            str((await sp.device(datapoint["exit_device_id"])).get("name")),
                        )

            console.print(table, "", sep="\n")

        await sp._session.close()


@cli.command()
@click.pass_context
@click.option("-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True)
@coro
async def notification(ctx: click.Context, token: Optional[str] = None) -> None:
    """get notifications"""

    if token := ctx.obj.get("token", find_token(token)):

        sp = SurePetcare(auth_token=str(token))

        if data := (await sp.get_notification()).get("data"):

            table = Table(box=box.MINIMAL)

            all_keys: Set[str] = set()
            all_keys.update(*[entry.keys() for entry in data])

            for key in all_keys:
                table.add_column(str(key))

            for entry in data:
                table.add_row(*([str(e) for e in entry.values()]))

            console.print(table, "", sep="\n")

        await sp._session.close()


@cli.command()
@click.pass_context
@click.option("-d", "--device", "device_id", required=True, type=int, help="id of the sure petcare device")
@click.option("-m", "--mode", required=True, type=click.Choice(["lock", "in", "out", "unlock"]), help="locking mode")
@click.option("-t", "--token", required=False, type=str, help="sure petcare api token", hide_input=True)
@coro
async def locking(ctx: click.Context, device_id: int, mode: str, token: Optional[str] = None) -> None:
    """lock control"""

    if token := ctx.obj.get("token", find_token(token)):

        sp = SurePetcare(auth_token=str(token))

        lock_control: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None

        if mode == "lock":
            lock_control = sp.lock
            state = "locked"
        elif mode == "in":
            lock_control = sp.lock_in
            state = "locked in"
        elif mode == "out":
            lock_control = sp.lock_out
            state = "locked out"
        elif mode == "unlock":
            lock_control = sp.unlock
            state = "unlocked"
        else:
            return

        with Halo(text=f"setting to '{state}'", spinner="dots", color="red") as spinner:

            if await lock_control(device_id=device_id) and (device := await sp.device(device_id=device_id)):
                spinner.succeed(f"{device.get('name')} set to '{state}' 🐾")
            else:
                spinner.fail(f"setting to '{state}' probably worked but something else is fishy...!")

        await sp._session.close()
        print()


if __name__ == "__main__":
    cli(obj={})
