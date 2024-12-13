import logging
import logging.config
import logging.handlers
import pathlib
from os import environ
from typing import Annotated, Any, Literal

import pydantic
import rich.logging
import typer

from acederbergio import util

logger = logging.getLogger(__name__)

ENV_PREFIX = "ACEDERBERG_IO"
ENV_POSSIBLE = {"development", "ci", "production"}
FieldEnv = Annotated[
    Literal["development", "ci", "production"],
    pydantic.Field(default="development"),
]


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

DEV = BUILD / "dev"


if (_ENV := require("env", "development").lower()) not in ENV_POSSIBLE:
    raise ValueError(f"Value for `env` must be one of `{ENV_POSSIBLE}`.")

ENV: FieldEnv = _ENV  # type: ignore
ENV_IS_DEV = ENV == "development"


def create_logging_config() -> dict[str, Any]:
    """Create the uvicorn logging config.

    This could be kept in a file. But if I decide to package this it can be a
    real pain to keep such files in the package. Furhter I do not want to
    maintain two configs.
    """

    # NOTE: Some handlers are underscored so that the alphetical order requirement of
    #       resolution (handlers to be resolved require a name of an earlier letter
    #       when using ``cfg://``.
    handlers: dict[str, Any] = {
        "_rich": {
            "class": "rich.logging.RichHandler",
        },
        "queue": {
            "class": "acederbergio.util.QueueHandler",
            "handlers": ["cfg://handlers._rich"],
        },
        "queue_no_stdout": {
            "class": "acederbergio.util.QueueHandler",
            "handlers": [],
        },
    }

    formatters: dict[str, Any] = {}
    if ENV_IS_DEV:
        formatters.update({"json": {"class": "acederbergio.util.JSONFormatter"}})

        handlers["queue"]["handlers"].append("cfg://handlers._socket")
        handlers["queue_no_stdout"]["handlers"].append("cfg://handlers._socket")
        handlers.update(
            {
                "_socket": {
                    "class": "acederbergio.util.SocketHandler",
                    "level": "INFO",
                    "host": str(ROOT / "blog.socket"),
                    "port": None,
                    "formatter": "json",
                },
            }
        )

    config_pandoc_filters = {"level": "INFO", "handlers": ["_socket"]}
    config_api = {"level": "INFO", "handlers": ["queue"]}
    out = {
        "version": 1,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            # NOTE: Cannot be added dynamically.
            "acederbergio.filters.dev": config_pandoc_filters,
            "acederbergio.filters.floaty": config_pandoc_filters,
            "acederbergio.filters.minipage": config_pandoc_filters,
            "acederbergio.filters.resume": config_pandoc_filters,
            "acederbergio.filters.under_construction": config_pandoc_filters,
            "acederbergio.filters.util": config_pandoc_filters,
            # API
            "acederbergio.api.base": config_api,
            "acederbergio.api.depends": config_api,
            "acederbergio.api.main": config_api,
            "acederbergio.api.quarto": config_api,
            "acederbergio.api.routes": config_api,
            "acederbergio.api.schemas": config_api,
            # ROOT
            "root": config_api,
        },
    }
    return out


LOGGING_CONFIG = create_logging_config()
logging.config.dictConfig(LOGGING_CONFIG)


def create_logger(name: str):
    """Create a logger."""

    level = require("log_level", "INFO").upper()
    logger = logging.getLogger(name)
    logger.propagate = False
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


@cli.command("logging")
def show_logging():
    util.print_yaml(LOGGING_CONFIG, name="Logging Configuration")
