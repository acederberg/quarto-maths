from http import HTTPMethod
from typing import Any, ClassVar

import fastapi

from acederbergio import env

logger = env.create_logger(__name__)


class RouterMixins:
    """

    :attr router_children: Dictionary of instances to instances.
    :attr router: The router built by :class:`ViewMeta`.
    :attr router: Mapping from router function names to router routes.
    """

    # router_children: ClassVar[dict[str, Type]] = dict()
    router_children: ClassVar[dict[str, "RouterMeta"]] = dict()
    router: ClassVar[fastapi.APIRouter | fastapi.FastAPI]
    router_args: ClassVar[dict[str, Any]] = dict()  # type: ignore
    router_routes: ClassVar[dict[str, str | dict[str, Any]]] = dict()  # type: ignore


class RouterMeta(type):
    """Metaclass to handle routing.

    It will build a router under `router`.
    """

    @classmethod
    def add_route(cls, T, fn_name: str, fn_info_raw: str | dict[str, Any]):
        name = T.__name__

        # NOTE: Annotation is stange bc of the following mypy error:
        #       Incompatible types in capture pattern (pattern captures type "dict[object, object]", variable has type "dict[str, Any]")  [misc]
        info: dict[Any, Any]
        url: str
        match fn_info_raw:
            case str() as url:
                info = dict()
            case {"url": url, **info}:
                ...
            case bad:
                msg = "Invalid info for url: Expected `str` for url or "
                msg += f"`dict` specifying atleast a url, got `{bad}`."
                raise ValueError(msg)

        # Parse name
        raw, _ = fn_name.split("_", 1)
        http_meth = next((hh for hh in HTTPMethod if hh.value.lower() == raw), None)
        if http_meth is None:
            logger.warning(f"Could not determine method of `{fn_name}`.")
            return

        # Update status code if not provided.
        if http_meth == HTTPMethod.POST and "status" not in info:
            info.update(status_code=201)

        # Find attr
        fn = getattr(T, fn_name, None)
        if fn is None:
            msg = f"No such method `{fn_name}` of `{name}`."
            raise ValueError(msg)

        # Get the decoerator and call it.
        logger.debug("Adding function `%s` at url `%s`.", fn.__name__, url)
        decorator = getattr(T.router, http_meth.value.lower())
        decorator(url, **info)(fn)

    def __new__(cls, name, bases, namespace):
        T = super().__new__(cls, name, bases, namespace)
        logger.debug("Validating `%s` router.", name)

        # Validate `router_children`.
        if not hasattr(T, "router_children"):
            raise ValueError(f"`{name}` must define `router_children`.")
        elif not isinstance(T.router_children, dict):  # type: ignore
            raise ValueError(f"`{name}.router_children` must be a `dict`.")

        # Validate `view`.
        if not hasattr(T, "router_routes"):
            raise ValueError(f"`{name}` must define `router`.")
        elif not isinstance(T.router_routes, dict):  # type: ignore
            raise ValueError(f"`{name}.router` must be a dict.")

        # Validate `router_args`.
        if not hasattr(T, "router_args"):
            raise ValueError(f"`{name}` must define `router_args`.")
        elif not isinstance(T.router_args, dict):  # type: ignore
            raise ValueError(f"`{name}.router_args` must be a `dict`.")

        if name != "BaseView":
            # Create router.
            logger.debug("Creating router for `%s`.", name)
            T.router = (  # type: ignore
                T.router  # type: ignore
                if hasattr(T, "router")
                else fastapi.APIRouter(**T.router_args)  # type: ignore
            )
            for fn_name, fn_info in T.router_routes.items():  # type: ignore
                cls.add_route(T, fn_name, fn_info)

            for child_prefix, child in T.router_children.items():  # type: ignore
                logger.debug(
                    "Adding child router `%s` for `%s`.",
                    child_prefix,
                    name,
                )
                T.router.include_router(  # type: ignore
                    child.router,
                    prefix=child_prefix,
                )

        return T


class Router(RouterMixins, metaclass=RouterMeta): ...
