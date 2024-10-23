import asyncio
import json
import logging
import os
import pathlib
import sys
from datetime import datetime
from typing import Annotated, Any, Optional

import httpx
import toml
import typer
import yaml

from scripts import env

logger = logging.getLogger(__name__)

QUARTO = env.BLOG / "_quarto.yaml"
QUARTO_VARIABLES = env.BLOG / "_variables.yaml"


class Context:
    dry: bool

    quarto_variables: pathlib.Path
    quarto: pathlib.Path

    def __init__(
        self,
        dry: bool,
        *,
        quarto: pathlib.Path = QUARTO,
        quarto_variables: pathlib.Path = QUARTO_VARIABLES,
    ):
        self.dry = dry
        self.quarto = quarto
        self.quarto_variables = quarto_variables

    def set_tracking_id(self, google_tracking_id: str):
        logger.debug("Loading `%s`.", self.quarto)
        with open(self.quarto, "r") as file:
            data = yaml.safe_load(file)

        logger.debug("Updating `%s`.", self.quarto)
        if (website := data.get("website")) is None:
            print(f"`{QUARTO}` does not contain required key `website`.")
            raise typer.Exit(101)

        # if website.get("google-analytics") is not None:
        #     print(f"`{QUARTO}` already has a value for `website.google-analytics`.")
        #     raise typer.Exit(102)

        website["google-analytics"] = google_tracking_id
        if self.dry:
            print("---")
            print("# _quarto.yaml\n")
            print(yaml.dump(website))
            return

        logger.debug("Dumping updated `%s`.", self.quarto)

        with open(self.quarto, "w") as file:
            yaml.safe_dump(data, file)

    def spawn_variables(
        self,
        build_git_commit,
        build_git_ref,
    ):

        logger.debug("Adding variables to ``_variables.yaml``.")
        now = datetime.now()
        data = {
            "build_git_commit": build_git_commit,
            "build_git_ref": build_git_ref,
            "build_timestamp": datetime.timestamp(now),
            "build_isoformat": now.isoformat(),
        }

        if self.dry:
            print("---")
            print("# _variables.yaml\n")
            print(yaml.dump(data))
            return

        with open(self.quarto_variables, "w") as file:
            yaml.dump(data, file)

    async def get_iconsets(self, config: dict[str, Any], include: set[str]) -> None:
        """See ``[tool.acederbergio.icons]`` in pyproject toml."""

        icons = config["tool"]["acederbergio"]["icons"]
        origin = icons["origin"]

        def create_url(iconset: dict[str, str]):
            _origin = iconset.get("origin", origin)

            url = f'{_origin}/{iconset["name"]}'
            if "version" in iconset:
                url += f'@{iconset["version"]}'

            url += "/icons.json"
            return url

        urls = {
            create_url(iconset): iconset
            for iconset in icons["sets"]
            if iconset["name"] in include
        }

        if self.dry:
            print("---")
            print("# iconsets")
            print(yaml.dump(urls))
            return

        await asyncio.gather(
            *(self.get_iconset(url, config) for url, config in urls.items())
        )

    async def get_iconset(self, url: str, config: dict[str, str]):
        destination = config["destination"]
        destination = env.ICONS_SETS / f"{destination}.json"

        if os.path.exists(destination):
            return

        response = httpx.get(url)
        if response.status_code != 200:
            print(f"Bad response status code `{response.status_code}` from `{url}`.")
            raise typer.Exit(103)

        with open(destination, "w") as file:
            json.dump(response.json(), file)


FlagBuildGitCommit = Annotated[Optional[str], typer.Option("--build-git-commit")]
FlagBuildGitRef = Annotated[Optional[str], typer.Option("--build-git-ref")]
FlagInclude = Annotated[list[str], typer.Option("--include")]
FlagGoogleTrackingId = Annotated[
    Optional[str],
    typer.Option("--google-tracking-id"),
]
FlagDry = Annotated[bool, typer.Option("--dry/--for-real")]


def create_context(context: typer.Context, dry: FlagDry = True):
    context_data = Context(dry)
    context.obj = context_data


cli = typer.Typer(callback=create_context)


@cli.command("google-analytics")
def google_analytics(
    _context: typer.Context, _google_tracking_id: FlagGoogleTrackingId = None
):

    context: Context = _context.obj
    google_tracking_id = env.require("google_tracking_id", _google_tracking_id)
    context.set_tracking_id(google_tracking_id)


@cli.command("build-info")
def build_info(
    _context: typer.Context,
    _build_git_commit: FlagBuildGitCommit = None,
    _build_git_ref: FlagBuildGitRef = None,
):
    # kubernetes_json = env.ICONS_SETS / "kubernetes.json"
    # if not os.path.exists(kubernetes_json):
    #     raise ValueError("Cannot find `{kubernetes_json}`.")

    context: Context = _context.obj
    build_git_commit = env.require("build_git_commit", _build_git_commit)
    build_git_ref = env.require("build_git_ref", _build_git_ref)

    context.spawn_variables(build_git_commit, build_git_ref)


@cli.command("icons")
def icons(
    _context: typer.Context,
    _include: FlagInclude = list(),
):

    with open(env.ROOT / "pyproject.toml", "r") as file:
        config = toml.load(file)

    if not _include:
        _include = list(
            item["name"] for item in config["tool"]["acederbergio"]["icons"]["sets"]
        )

    context: Context = _context.obj
    include = set(_include)
    asyncio.run(context.get_iconsets(config, include))


@cli.command("all")
def main(
    _context: typer.Context,
    _build_git_commit: FlagBuildGitCommit = None,
    _build_git_ref: FlagBuildGitRef = None,
    _google_tracking_id: FlagGoogleTrackingId = None,
    _include: FlagInclude = list(),
):
    google_analytics(_context, _google_tracking_id)
    build_info(_context, _build_git_commit, _build_git_ref)
    icons(_context, _include)


if __name__ == "__main__":
    cli()
