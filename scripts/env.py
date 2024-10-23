import logging
import pathlib
from os import environ

import typer

logger = logging.getLogger(__name__)

ENV_PREFIX = "ACEDERBERG_IO"

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
BUILD = BLOG / "build"
ICONS = BLOG / "icons"
ICONS_SETS = ICONS / "sets"


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
        print(f"Value `{var}` for `{varname}` is falsy.")
        raise typer.Exit(2)

    return var
