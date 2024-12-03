from http import HTTPMethod
from typing import Any, ClassVar

import fastapi

from acederbergio import env
from acederbergio.api import schemas

logger = env.create_logger(__name__)

AnyRouter = fastapi.APIRouter | fastapi.FastAPI


class RouterMixins:
    """

    :attr router_children: Dictionary of instances to instances.
    :attr router: The router built by :class:`ViewMeta`.
    :attr router: Mapping from router function names to router routes.
    """

    # router_children: ClassVar[dict[str, Type]] = dict()
    router_children: ClassVar[dict[str, "RouterMeta"]] = dict()
    router: ClassVar[AnyRouter]
    router_args: ClassVar[dict[str, Any]] = dict()  # type: ignore
    router_routes: ClassVar[dict[str, str | dict[str, Any]]] = dict()  # type: ignore

    @classmethod
    async def get_routes(cls, request: fastapi.Request) -> schemas.AppInfo:
        prefix = request.url.path.replace("/routes", "")
        return schemas.AppInfo.fromRouter(cls.router, prefix=prefix)

    @staticmethod
    def get_it_works():
        return "It works!"


class RouterMeta(type):
    """Metaclass to handle routing.

    It will build a router under `router`.
    """

    @classmethod
    def add_route(
        cls, T, router: AnyRouter, *, fn_name: str, fn_info_raw: str | dict[str, Any]
    ):
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
        if raw == "websocket":
            meth = "websocket"
        else:
            meth = next((hh for hh in HTTPMethod if hh.value.lower() == raw), None)
            if meth is None:
                logger.warning(f"Could not determine method of `{fn_name}`.")
                return

            # Update status code if not provided.
            if meth == HTTPMethod.POST and "status" not in info:
                info.update(status_code=201)

            meth = meth.value.lower()

        # Find attr
        fn = getattr(T, fn_name, None)
        if fn is None:
            msg = f"No such method `{fn_name}` of `{name}`."
            raise ValueError(msg)

        # Get the decoerator and call it.
        logger.debug("Adding function `%s` at url `%s`.", fn.__name__, url)
        decorator = getattr(router, meth.lower())
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
            logger.debug("Creating router for `%s`.", name)
            router = (  # type: ignore
                T.router  # type: ignore
                if hasattr(T, "router")
                else fastapi.APIRouter(**T.router_args)  # type: ignore
            )
            cls.create_router(T, router)
            T.router = router

        return T

    @classmethod
    def create_router(cls, T, router: AnyRouter):
        # Create router.
        for fn_name, fn_info in T.router_routes.items():  # type: ignore
            cls.add_route(T, router, fn_name=fn_name, fn_info_raw=fn_info)

        for child_prefix, child in T.router_children.items():  # type: ignore
            router.include_router(  # type: ignore
                child.router,
                prefix=child_prefix,
            )


class Router(RouterMixins, metaclass=RouterMeta): ...
