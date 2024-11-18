import asyncio
import json
import os
import pathlib
import re
from typing import Annotated, Any, Literal, Optional

import git
import httpx
import pydantic
import rich
import toml
import typer
import yaml

from acederbergio import env, util

logger = env.create_logger(__name__)

QUARTO = env.BLOG / "_quarto.yaml"
QUARTO_VARIABLES = env.BLOG / "_variables.yaml"

AnnouncementPositionValues = {"above-navbar", "below-navbar"}
AnnouncementPosition = Literal["below-navbar", "above-navbar"]
AnnouncementTypeValues = {
    "primary",
    "secondary",
    "success",
    "danger",
    "warning",
    "info",
    "light",
    "dark",
}
AnnouncementType = Literal[
    "primary",
    "secondary",
    "success",
    "danger",
    "warning",
    "info",
    "light",
    "dark",
]


def validate_commit_hash(value):
    if not re.fullmatch("[0-9a-f]{40}", value):
        raise ValueError(
            "Invalid Git Commit Hash: Must be a 40-character hexadecimal string."
        )
    return value


FieldGitHash = Annotated[
    str,
    pydantic.Field(),
    pydantic.BeforeValidator(validate_commit_hash),
]


class BuildInfo(util.HasTimestamp):
    git_ref: Annotated[str, pydantic.Field()]
    git_commit: FieldGitHash

    @classmethod
    def fromRepo(
        cls,
        _git_commit: str | None = None,
        _git_ref: str | None = None,
    ):
        _git_commit = env.get("build_git_commit", _git_commit)
        _git_ref = env.get("build_git_ref", _git_ref)

        repo = git.Repo(env.ROOT)
        git_ref = _git_ref or str(repo.head.ref)
        git_commit = _git_commit or str(repo.head.commit)

        return cls(git_ref=git_ref, git_commit=git_commit)  # type: ignore


class Context:
    dry: bool
    preview: bool

    build_json: pathlib.Path
    quarto_variables: pathlib.Path
    quarto: pathlib.Path
    _quarto_config: None | dict[str, Any]

    def __init__(
        self,
        dry: bool,
        *,
        preview: bool = True,
        quarto: pathlib.Path = QUARTO,
        quarto_variables: pathlib.Path = QUARTO_VARIABLES,
        build_json: pathlib.Path = env.BUILD_JSON,
    ):
        self.dry = dry
        self.preview = preview

        self.build_json = build_json
        self.quarto = quarto
        self.quarto_variables = quarto_variables
        self._quarto_config = None

    @property
    def quarto_config(self) -> dict[str, Any]:
        logger.debug("Loading `%s`.", self.quarto)
        if self._quarto_config is not None:
            return self._quarto_config

        with open(self.quarto, "r") as file:
            data = yaml.safe_load(file)

        self._quarto_config = data
        return data

    def quarto_config_save(self) -> None:
        logger.debug("Dumping updated `%s`.", self.quarto)
        with open(self.quarto, "w") as file:
            yaml.safe_dump(self.quarto_config, file)

    def set_tracking_id(self, google_tracking_id: str):
        data = self.quarto_config

        logger.debug("Updating `%s`.", self.quarto)
        if (website := data.get("website")) is None:
            print(f"`{QUARTO}` does not contain required key `website`.")
            raise typer.Exit(101)

        # if website.get("google-analytics") is not None:
        #     print(f"`{QUARTO}` already has a value for `website.google-analytics`.")
        #     raise typer.Exit(102)

        website["google-analytics"] = google_tracking_id
        if self.dry:
            util.print_yaml(
                self.quarto_config["website"]["google-analytics"],
                name="_quarto.yaml website.google-analytics",
            )

        self.quarto_config_save()

    def set_announcement(
        self,
        content: str,
        *,
        type_: AnnouncementType,
        position: AnnouncementPosition,
    ):
        announcement = {
            "icon": "arrow-down",
            "dismissable": True,
            "content": content,
            "type": type_,
            "position": position,
        }
        self.quarto_config["website"].update(announcement=announcement)
        if self.dry:
            util.print_yaml(
                self.quarto_config["website"]["announcement"],
                name="_quarto.yaml website.announcement",
            )
            return

        self.quarto_config_save()

        return

    def spawn_variables(
        self,
        *,
        _git_commit: str | None = None,
        _git_ref: str | None = None,
    ):

        logger.debug("Adding variables to ``_variables.yaml``.")
        data = BuildInfo.fromRepo(
            _git_commit=_git_commit,
            _git_ref=_git_ref,
        ).model_dump(mode="json")

        if self.dry:
            util.print_yaml(data, name="_variables.yaml")
            return

        with open(self.quarto_variables, "w") as file:
            yaml.dump(data, file)

        with open(self.build_json, "w") as file:
            json.dump(data, file)

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
            util.print_yaml(urls, name="iconsets")
            return

        await asyncio.gather(
            *(self.get_iconset(url, config) for url, config in urls.items())
        )

    async def get_iconset(self, url: str, config: dict[str, str]):
        destination = env.ICONS_SETS / f"{config['destination']}.json"
        if os.path.exists(destination):
            return

        response = httpx.get(url)
        if response.status_code != 200:
            print(f"Bad response status code `{response.status_code}` from `{url}`.")
            raise typer.Exit(103)

        with open(destination, "w") as file:
            json.dump(response.json(), file)


FlagBuildGitCommit = Annotated[
    Optional[str],
    typer.Option(
        "--build-git-commit",
        help="Git commit to put into the build information page.",
    ),
]
FlagBuildGitRef = Annotated[
    Optional[str],
    typer.Option(
        "--build-git-ref",
        help="Git commit to put into the build information page.",
    ),
]
FlagIconsetsInclude = Annotated[
    list[str],
    typer.Option(
        "--include",
        help="Which iconify iconsets to include. Mostly for tests.",
    ),
]
FlagGoogleTrackingId = Annotated[
    Optional[str],
    typer.Option("--google-tracking-id"),
]
FlagDry = Annotated[
    bool,
    typer.Option(
        "--dry/--for-real",
        help="Do a dry run or not.",
    ),
]

FlagAnnouncementContent = Annotated[
    str,
    typer.Option("--content", help="Content for the announcement."),
]

FlagAnnouncementType = Annotated[
    str,
    typer.Option("--type", help="Color of the announcement bar."),
]
FlagAnnouncementPosition = Annotated[
    str,
    typer.Option("--position", help="Position of the announcement bar."),
]
FlagPreview = Annotated[
    bool,
    typer.Option(
        "--preview/--production",
        help="Is this reconfiguration for the production site?",
    ),
]


def create_context(
    context: typer.Context,
    dry: FlagDry = True,
    preview: FlagPreview = False,
):
    env_preview = env.get("preview") == "1"
    context_data = Context(dry, preview=preview or env_preview)
    context.obj = context_data


cli = typer.Typer(callback=create_context)


@cli.command("google-analytics")
def google_analytics(
    _context: typer.Context, _google_tracking_id: FlagGoogleTrackingId = None
):

    context: Context = _context.obj
    google_tracking_id = env.require("google_tracking_id", _google_tracking_id)
    context.set_tracking_id(google_tracking_id)


@cli.command("announcement")
def announcement(
    _context: typer.Context,
    content: FlagAnnouncementContent,
    position: FlagAnnouncementPosition = "below-navbar",
    type_: FlagAnnouncementType = "success",
):
    if position not in AnnouncementPositionValues:
        rich.print(
            f"[red]Invalid value `{position}` for `--position`, "
            "must be one of `AnnouncementPositionValues`."
        )
        raise typer.Exit(104)

    if type_ not in AnnouncementTypeValues:
        rich.print(
            f"[red]Invalid value `{type_}` for `--type`, "
            "must be one of `AnnouncementPositionValues`."
        )
        raise typer.Exit(105)

    context: Context = _context.obj
    context.set_announcement(content, position=position, type_=type_)  # type: ignore


@cli.command("build-info")
def build_info(
    _context: typer.Context,
    _git_commit: FlagBuildGitCommit = None,
    _git_ref: FlagBuildGitRef = None,
):
    # kubernetes_json = env.ICONS_SETS / "kubernetes.json"
    # if not os.path.exists(kubernetes_json):
    #     raise ValueError("Cannot find `{kubernetes_json}`.")

    context: Context = _context.obj
    context.spawn_variables(_git_commit=_git_commit, _git_ref=_git_ref)


@cli.command("icons")
def icons(
    _context: typer.Context,
    _include: FlagIconsetsInclude = list(),
):

    with open(env.PYPROJECT_TOML, "r") as file:
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
    _include: FlagIconsetsInclude = list(),
    content: FlagAnnouncementContent = "This is a preview build.",
    position: FlagAnnouncementPosition = "below-navbar",
    type_: FlagAnnouncementType = "success",
):
    context: Context = _context.obj
    google_analytics(_context, _google_tracking_id)
    if context.preview:
        announcement(_context, content, position=position, type_=type_)

    build_info(_context, _build_git_commit, _build_git_ref)
    icons(_context, _include)


if __name__ == "__main__":
    cli()
