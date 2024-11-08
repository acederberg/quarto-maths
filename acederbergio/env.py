import logging
import pathlib
from os import environ

import rich.logging
import typer
import yaml
from rich import syntax

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.WARNING,
    handlers=[rich.logging.RichHandler()],
    format="%(message)s",
)

ENV_PREFIX = "ACEDERBERG_IO"


def get(
    varname: str, default: str | None = None, *, required: bool = False
) -> str | None:

    logger.debug("Getting variable `%s`.", varname)
    out = environ.get(f"{ENV_PREFIX}_{varname.upper()}", default)
    if out is None and required:
        print(f"Could not resolve for variable `{varname}`.")
        raise typer.Exit(1)

    return out


def require(varname: str, default: str | None = None) -> str:

    var = get(varname, default, required=True)  # type: ignore
    if not var:
        rich.print(f"[red]Value `{var}` for `{varname}` is falsy.")
        raise typer.Exit(2)

    return var


def require_path(varname: str, default: pathlib.Path | None = None) -> pathlib.Path:

    var = get(varname)
    if var is not None:
        return pathlib.Path(var).resolve(strict=True)

    if default is None:
        rich.print(f"[red]Value `{var}` for `{varname}` is falsy.")
        raise typer.Exit(3)

    return default


ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = require_path("scripts", ROOT / "acederbergio")

# If installed directly.
if ROOT.parts[-1] != "site-packages":
    BLOG = ROOT / "blog"
    BUILD = BLOG / "build"
    ICONS = BLOG / "icons"
    PYPROJECT_TOML = ROOT / "pyproject.toml"

else:
    # NOTE: When fully installed, must export ACEDERBERGIO_BLOG and ACEDERBERGIO_BUILD
    #       since they will not be included.
    BLOG = require_path("blog")
    PYPROJECT_TOML = require_path("pyproject_toml")

    BUILD = require_path("build", BLOG / "build")
    ICONS = require_path("icons", BLOG / "icons")

ICONS_SETS = require_path("icon_sets", ICONS / "sets")


def create_logger(name: str):

    level = require("log_level", "WARNING")
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return logger


cli = typer.Typer()


@cli.command("show")
def show_environ():
    rich.print(
        syntax.Syntax(
            "---\n"
            + yaml.dump(
                {
                    "root": str(ROOT),
                    "scripts": str(SCRIPTS),
                    "blog": str(BLOG),
                    "build": str(BUILD),
                    "icons": str(ICONS),
                    "icon_sets": str(ICONS_SETS),
                }
            ),
            "yaml",
            theme="fuity",
            background_color="default",
        )
    )