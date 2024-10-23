import asyncio
import json
import logging
import pathlib
import sys
from datetime import datetime
from typing import Annotated, Optional

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

        if website.get("google-analytics") is not None:
            print(f"`{QUARTO}` already has a value for `website.google-analytics`.")
            raise typer.Exit(102)

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

    async def get_iconsets(self, exclude: set[str]) -> None:
        """See ``[tool.acederbergio.icons]`` in pyproject toml."""

        with open(env.ROOT / "pyproject.toml", "r") as file:
            config = toml.load(file)

        icons = config["tool"]["acederbergio"]["icons"]
        origin = icons["origin"]

        def create_name(iconset: dict[str, str]):
            _origin = iconset.get("origin", origin)

            url = f'{_origin}:{iconset["name"]}'
            if "version" in iconset:
                url += f'@{iconset["version"]}'

            url += "/icons.json"
            return url

        urls = (
            create_name(iconset)
            for iconset in icons["sets"]
            if iconset["name"] not in exclude
        )

        if self.dry:
            print("---")
            print("# iconsets")
            print(yaml.dump(list(urls)))
            return

        responses = zip(await asyncio.gather(*map(httpx.get, urls)), origin["sets"])
        for response, config in responses:
            self._dump_iconset(response, config)

    def _dump_iconset(self, response: httpx.Response, config: dict[str, str]):
        name = config
        destination = env.ICONS_SETS / f"{name}.json"
        with open(destination, "r") as file:
            json.dump(file, response.json())


def create_context(context: typer.Context, dry: bool = True):
    context_data = Context(dry)
    context.obj = context_data


cli = typer.Typer(callback=create_context)

FlagBuildGitCommit = Annotated[Optional[str], typer.Option("--build-git-commit")]
FlagBuildGitRef = Annotated[Optional[str], typer.Option("--build-git-ref")]
FlagExclude = Annotated[list[str], typer.Option("--exclude")]
FlagGoogleTrackingId = Annotated[
    Optional[str],
    typer.Option("--google-tracking-id"),
]


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
    _exclude: FlagExclude = list(),
):
    context: Context = _context.obj
    exclude = set(_exclude)
    asyncio.run(context.get_iconsets(exclude))


@cli.command()
def main(
    _context: typer.Context,
    _build_git_commit: FlagBuildGitCommit = None,
    _build_git_ref: FlagBuildGitRef = None,
    _google_tracking_id: FlagGoogleTrackingId = None,
    _exclude: FlagExclude = list(),
):
    google_analytics(_context, _google_tracking_id)
    build_info(_context, _build_git_commit, _build_git_ref)
    icons(_context, _exclude)


if __name__ == "__main__":
    cli()
