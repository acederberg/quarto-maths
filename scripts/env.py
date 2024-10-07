from os import environ
import pathlib

import logging

logger = logging.getLogger(__name__)

ENV_PREFIX = "ACEDERBERG_IO"

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
BUILD = BLOG / "build"


def get(
    varname: str, default: str | None = None, *, required: bool = False
) -> str | None:

    logger.debug("Getting variable `%s`.", varname)
    out = environ.get(f"{ENV_PREFIX}_{varname.upper()}", default)
    if out is None and required:
        raise ValueError(f"Could not resolve for variable `{varname}`.")

    return out


def require(varname: str, default: str | None = None) -> str:

    var = get(varname, default, required=True)  # type: ignore
    if not var:
        raise ValueError(f"Value `{var}` for `{varname}` is falsy.")

    return var
