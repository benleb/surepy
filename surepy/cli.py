#!/usr/bin/env python3

from typing import Any, Callable
import click

from surepy import SurePetcare, __name__ as sp_name, __version__ as sp_version


import asyncio
from functools import wraps


def coro(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

version_message = f"{sp_name} {sp_version} | https://github.com/benleb/surepy | @benleb"


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
@click.option("--version", default=False, is_flag=True, help=f"show {sp_name} version")
@click.option("-v", "--verbose", default=False, is_flag=True, help="enable additional output")
@click.option("-d", "--debug", default=False, is_flag=True, help="enable debug output")
def cli(ctx: click.Context, version: bool, verbose: bool, debug: bool) -> None:
    """surepy cli 🐾

    https://github.com/benleb/surepy
    """

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug

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
    """get token from sure petcare api"""

    sp = SurePetcare(email=user, password=password)

    if not sp._auth_token:
        await sp._refresh_token()
        await sp._session.close()

    click.echo()
    click.secho(version_message)
    click.echo()
    click.secho(f"Token: {sp._auth_token}", bold=True)
    click.echo()


if __name__ == "__main__":
    cli(obj={})
