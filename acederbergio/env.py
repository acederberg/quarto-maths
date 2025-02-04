"""
This module contains all of the tools used to get information from the environment.
It also contains command line tools to inspect the the environment, which are a 
great aid in debugging.
"""

import logging
import logging.config
import logging.handlers
import pathlib
import secrets
from os import environ
from typing import Annotated, Any, Literal

import pydantic
import rich.logging
import typer
from typing_extensions import Doc

from acederbergio import util

logger = logging.getLogger(__name__)

ENV_PREFIX = "ACEDERBERG_IO"
ENV_POSSIBLE = {"development", "ci", "production"}
FieldEnv = Annotated[
    Literal["development", "ci", "production"],
    pydantic.Field(default="development"),
]
RUN_UUID: Annotated[
    str, Doc("Used to keep track of the current ``docker`` container lifetime.")
]
RUN_UUID = secrets.token_urlsafe()


def name(varname: str) -> str:
    """Calculate the evironment variable name for a variable.

    For example, if we have a variable called ``thing`` then we should expect
    that it has the environment variable name ``ACEDERBERG_IO_THING``.

    :param varname: The variable name. For clarity, this should match the name the value is assigned to.
    :returns: The environment variable name for the variable.
    """
    return f"{ENV_PREFIX}_{varname.upper()}"


def get(
    varname: str, default: str | None = None, *, required: bool = False
) -> str | None:
    """Get an environment variable value for variable name.

    :param default: The default value to use if nothing is found.
    :param required: Raise an error to make the command line tool exit if
        no value is ascertained.
    :returns: The environment variable value or the default if provided.
    """

    logger.debug("Getting variable `%s`.", varname)
    out = environ.get(name(varname), default)
    if out is None and required:
        rich.print(f"[red]Could not resolve for variable `{varname}`.")
        raise typer.Exit(1)

    return out


def require(varname: str, default: str | None = None) -> str:
    """Require a setting from the environment using its short name.

    :param varname: (Short) variable name.
    :param default: Optional default value.
    :raises ValueError: When no value is ascertained.
    :returns: The environment variable value or the default provided.
    """

    var = get(varname, default, required=True)  # type: ignore
    if not var:
        raise ValueError(f"Value `{var}` for `{varname}` is falsy.")

    return var


def require_path(
    varname: str, default: pathlib.Path | None = None, *, strict: bool = True
) -> pathlib.Path:
    """Require a setting  from environment that is an existing path.

    Resolves path to be absolute and ensures existance.

    :param varname: (Short) variable name.
    :param default: Default pathlib`
    :raises ValueError: When no value can be ascertained.
    :returns: Path from env (as specified by :param:`varname` or :param:`default`.
    """

    var = get(varname)
    if var is not None:
        return pathlib.Path(var).resolve(strict=strict)

    if default is None:
        raise ValueError(f"Value `{var}` for `{varname}` is falsy.")

    return default.resolve(strict=strict)


def create_validator(varname: str, default: str | None = None):
    """Make a validator for ``varname``."""

    # NOTE: default < env < flag
    def validator(v: Any) -> Any:
        if v is not None:
            return v
        fook = get(varname, default)
        return fook

    return pydantic.AfterValidator(validator)


WORKDIR: Annotated[
    pathlib.Path,
    Doc(
        """
        When in development mode this should be the project root.
        Otherwise (e.g. in docker) this should be set the docker workdir.
        Ideally the workdir looks like the project root minus the ``acederbergio``
        folder.
        This setting is very important for features like

        - the quarto watcher (in `api.quarto`),
        - quarto api endpoints (in `api.routes`),
        - and filters that specify files.

        """
    ),
]

ROOT: Annotated[
    pathlib.Path,
    Doc(
        """ 
        For most cases just use ``WORKDIR``.

        In the development mode this should be the root directory of the git repository.
        However when installed as a package (e.g. in docker builds) this should be
        the directory in which the package is installed.
        """
    ),
]
BLOG: Annotated[pathlib.Path, Doc("Path to blog source code.")]
SCRIPTS: Annotated[pathlib.Path, Doc("Path to the ``acederbergio`` module.")]


ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = require_path("scripts", ROOT / "acederbergio")

# If installed in editable mode.
if ROOT.parts[-1] != "site-packages":
    BLOG = ROOT / "blog"
    WORKDIR = ROOT
    PYPROJECT_TOML = ROOT / "pyproject.toml"
    CONFIGS = require_path("config_dir", ROOT / "config", strict=False)

    BUILD = BLOG / "build"
    ICONS = BLOG / "icons"

else:
    # NOTE:
    WORKDIR = require_path("workdir")
    BLOG = require_path("blog", WORKDIR / "blog")
    PYPROJECT_TOML = require_path("pyproject_toml", WORKDIR / "pyproject.toml")
    CONFIGS = require_path("config_dir", pathlib.Path.home() / "config", strict=False)

    BUILD = require_path("build", BLOG / "build")
    ICONS = require_path("icons", BLOG / "icons")

VERBOSE = require("verbose", "0") != "0"
TEMPLATES = require_path("templates", SCRIPTS / "templates")
ICONS_SETS = require_path("icon_sets", ICONS / "sets")
BUILD_JSON = require_path("build_json", BLOG / "build.json")

LEVEL = require("log_level", "INFO").upper()
LEVEL_FILTERS = require("log_level_filters", LEVEL).upper()
LEVEL_API = require("log_level_api", LEVEL).upper()

DEV = BUILD / "dev"


if (_ENV := require("env", "development").lower()) not in ENV_POSSIBLE:
    raise ValueError(f"Value for `env` must be one of `{ENV_POSSIBLE}`.")

ENV: FieldEnv = _ENV  # type: ignore
ENV_IS_DEV = ENV == "development"


def create_logging_config() -> dict[str, Any]:
    """Create the uvicorn logging config.

    .. This could be kept in a file. But if I decide to package this it can be a
       real pain to keep such files in the package. Further I do not want to
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

    formatters: dict[str, Any]
    formatters = {"json": {"class": "acederbergio.util.JSONFormatter"}}

    if ENV_IS_DEV:
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
    else:
        # NOTE: Add build logs to build in ci mode.
        handlers.update(
            {
                "_file": {
                    "class": "logging.FileHandler",
                    "level": LEVEL_FILTERS,
                    "formatter": "json",
                    "filename": str(BUILD / "build.jsonl"),
                }
            }
        )
        config_pandoc_filters = {"level": LEVEL_FILTERS, "handlers": ["_file"]}

    config_api = {"level": LEVEL_API, "handlers": ["queue"]}
    config_rest = {"level": LEVEL, "handlers": ["_rich"]}
    out = {
        "version": 1,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            # NOTE: Cannot be added dynamically.
            "acederbergio.filters.dev": config_pandoc_filters,
            "acederbergio.filters.floaty": config_pandoc_filters,
            "acederbergio.filters.minipage": config_pandoc_filters,
            "acederbergio.filters.contacts": config_pandoc_filters,
            "acederbergio.filters.links": config_pandoc_filters,
            "acederbergio.filters.resume": config_pandoc_filters,
            "acederbergio.filters.skills": config_pandoc_filters,
            "acederbergio.filters.under_construction": config_pandoc_filters,
            "acederbergio.filters.iframe": config_pandoc_filters,
            "acederbergio.filters.util": config_pandoc_filters,
            "acederbergio.filters.live": config_pandoc_filters,
            # API
            "acederbergio.api.base": config_api,
            "acederbergio.api.depends": config_api,
            "acederbergio.api.main": config_api,
            "acederbergio.api.quarto": config_api,
            "acederbergio.api.routes": config_api,
            "acederbergio.api.schemas": config_api,
            # ETC
            "acederbergio.pdf": config_rest,
            # ROOT. Do not propogate to this. Logging propagation is stupid and
            # can cause
            "root": config_api,
            "watchfiles.main": {"level": "WARNING"},
        },
    }
    return out


LOGGING_CONFIG = create_logging_config()
logging.config.dictConfig(LOGGING_CONFIG)


def create_logger(name: str) -> logging.Logger:
    """Create a logger.

    :param name: Name of the logger.
    :returns: A configured logger.
    """

    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(LEVEL)

    return logger


cli = typer.Typer(help="Environment variables tools.")


@cli.command("find")
def cli_find(varnames: list[str]):
    """
    Show environment name for a variable.
    """

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
def cli_show_environ():
    """
    Show the current environment as interpretted by ``env.py``. Note that
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
            "templates": str(TEMPLATES),
            "verbose": str(VERBOSE),
            "level": LEVEL,
        },
        name="variables",
    )


@cli.command("logging")
def cli_show_logging():
    util.print_yaml(LOGGING_CONFIG, name="Logging Configuration")
