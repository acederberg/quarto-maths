import logging
import pathlib
from os import environ
from typing import Any

import pydantic
import rich.logging
import typer
import yaml
from rich import syntax

from acederbergio import util

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.WARNING,
    handlers=[rich.logging.RichHandler()],
    format="%(message)s",
)

ENV_PREFIX = "ACEDERBERG_IO"


def name(varname: str) -> str:
    return f"{ENV_PREFIX}_{varname.upper()}"


def get(
    varname: str, default: str | None = None, *, required: bool = False
) -> str | None:

    logger.debug("Getting variable `%s`.", varname)
    out = environ.get(name(varname), default)
    if out is None and required:
        rich.print(f"[red]Could not resolve for variable `{varname}`.")
        raise typer.Exit(1)

    return out


def require(varname: str, default: str | None = None) -> str:
    """Require a setting from the environment."""

    var = get(varname, default, required=True)  # type: ignore
    if not var:
        rich.print(f"[red]Value `{var}` for `{varname}` is falsy.")
        raise typer.Exit(2)

    return var


def require_path(varname: str, default: pathlib.Path | None = None) -> pathlib.Path:
    """Require a setting  from environment that is an actual path."""

    var = get(varname)
    if var is not None:
        return pathlib.Path(var).resolve(strict=True)

    if default is None:
        rich.print(f"[red]Value `{var}` for `{varname}` is falsy.")
        raise typer.Exit(3)

    return default


def create_validator(varname: str, default: str | None = None):
    """Make a validator for ``varname``."""

    # NOTE: default < env < flag
    def validator(v: Any) -> Any:
        if v is not None:
            return v
        fook = get(varname, default)
        return fook

    return pydantic.AfterValidator(validator)


ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = require_path("scripts", ROOT / "acederbergio")

# If installed directly.
if ROOT.parts[-1] != "site-packages":
    BLOG = ROOT / "blog"
    PYPROJECT_TOML = ROOT / "pyproject.toml"
    CONFIGS = require_path("config_dir", ROOT / "config")

    BUILD = BLOG / "build"
    ICONS = BLOG / "icons"

else:
    # NOTE: When fully installed, must export ACEDERBERGIO_BLOG and ACEDERBERGIO_BUILD
    #       since they will not be included.
    BLOG = require_path("blog")
    PYPROJECT_TOML = require_path("pyproject_toml")
    CONFIGS = require_path("config_dir", pathlib.Path.home() / "config")

    BUILD = require_path("build", BLOG / "build")
    ICONS = require_path("icons", BLOG / "icons")

ICONS_SETS = require_path("icon_sets", ICONS / "sets")
BUILD_JSON = require_path("build_json", BLOG / "build.json")


def create_logger(name: str):

    level = require("log_level", "WARNING")
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return logger


cli = typer.Typer(help="Environment variables tools.")


@cli.command("find")
def find(varnames: list[str]):
    """Show environment name for a variable."""

    util.print_yaml(
        [
            {
                "name": varname,
                "name_env": name(varname),
                "value": get(varname),
            }
            for varname in varnames
        ],
        name="found",
    )


@cli.command("show")
def show_environ():
    """Show the current environment as interpretted by ``env.py``. Note that
    not all of these are able to be set directly.
    """
    util.print_yaml(
        {
            "root": str(ROOT),
            "scripts": str(SCRIPTS),
            "blog": str(BLOG),
            "build": str(BUILD),
            "icons": str(ICONS),
            "icon_sets": str(ICONS_SETS),
            "configs": str(CONFIGS),
        },
        name="variables",
    )
