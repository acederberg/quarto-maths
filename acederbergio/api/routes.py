import asyncio
from typing import Any, ClassVar, TypeVar

import fastapi
import fastapi.routing
import pydantic
from fastapi.websockets import WebSocketState

from acederbergio import env
from acederbergio.api import base, depends, schemas

logger = env.create_logger(__name__)

T_BaseLog = TypeVar("T_BaseLog", bound=schemas.BaseLog)


class LogRoutesMixins:
    """Generics help write less code in a way that type hints are happy.

    The problem is that ``fastapi`` does not resolve the annotations, so children
    will provide wrappers with annotations that ``fastapi`` will find okay.
    """

    @classmethod
    async def get(
        cls, s: type[T_BaseLog], database: depends.Db, *, ws: bool = False, **kwargs
    ) -> T_BaseLog | None:

        data = await s.latest(database, **kwargs)
        if data is None:
            if not ws:
                raise fastapi.HTTPException(204, detail={"msg": "No log data found."})
            return None

        # print(env.get("UVICORN_IDENTIFIER", secrets.token_urlsafe()))
        return data

    @classmethod
    async def delete(cls, s: type[T_BaseLog], database: depends.Db):
        res = await s.clear(database)
        return res

    @classmethod
    async def status(cls, s: type[T_BaseLog], database: depends.Db):
        count = await s.status(database)
        return schemas.LogStatus(count=count)

    @classmethod
    async def ws(
        cls,
        s: type[T_BaseLog],
        websocket: fastapi.WebSocket,
        database: depends.Db,
        last: int = 0,
        **kwargs,
    ):

        # NOTE: Must listen to hear disconnects. Without this, the websocket
        #       will never exit (which is what was causing reload to hang.
        #       Initially I assuemd this was from lifespan events but found that
        #       the server was still listening from print statements.
        async def listen():
            while websocket.client_state == WebSocketState.CONNECTED:
                await websocket.receive()

        await asyncio.gather(
            listen(),
            cls.ws_send(s, websocket, database, last=last, **kwargs),
        )
        # NOTE: Does not call ``close`` since closing is only on the part of
        #       client or on uvicorn reloads.

    @classmethod
    async def ws_send(
        cls,
        s: type[T_BaseLog],
        websocket: fastapi.WebSocket,
        database: depends.Db,
        *,
        last: int = 32,
        **kwargs,
    ) -> None:

        # NOTE: Push out the initial logs.
        log = await cls.get(s, database, ws=True, **kwargs)
        if last:
            if log is not None:
                log.items = log.items[-1 - last :]  # type: ignore
            await websocket.send_json(
                log if log is None else log.model_dump(mode="json")
            )

        count = 0 if log is None else log.count
        while websocket.client_state == WebSocketState.CONNECTED:
            await asyncio.sleep(3)

            data = await cls.get(
                s,
                database,
                slice_start=count,
                slice_count=128,
                ws=True,
                **kwargs,
            )
            if data is None or not data.count:
                continue

            try:
                await websocket.send_json(data.model_dump(mode="json"))
            except RuntimeError as err:
                if err.args[0].startswith("Unexpected ASGI message"):
                    return

                raise err
            count += data.count


# TODO: Make router generic.
class LogRoutes(LogRoutesMixins, base.Router):
    """View fastapi logs in dev application.

    Logs are first written into a unix socket in ``dev.Watcher`` and then
    pushed to mongodb.
    """

    router = fastapi.APIRouter()
    router_routes: ClassVar[dict[str, str | dict[str, Any]]] = {
        "get_log": dict(url=""),
        "get_log_status": dict(url="/status"),
        "delete_log": dict(url=""),
        "get_routes": dict(url="/routes"),
        "websocket_log": dict(url=""),
    }

    @classmethod
    async def get_log(
        cls,
        database: depends.Db,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ) -> schemas.Log:
        """Get the log for the current instance.

        This will update everytime that uvicorn reloads.
        """
        return await cls.get(  # type: ignore
            schemas.Log,
            database,
            slice_start=slice_start,
            slice_count=slice_count,
        )

    @classmethod
    async def get_log_status(cls, database: depends.Db) -> schemas.LogStatus:
        """Collection statyus report."""

        return await cls.status(schemas.Log, database)

    @classmethod
    async def delete_log(cls, database: depends.Db) -> int:
        """Clear all besides the current log."""

        res = await cls.delete(schemas.Log, database)
        return res.deleted_count

    @classmethod
    async def websocket_log(
        cls,
        websocket: fastapi.WebSocket,
        database: depends.Db,
    ):
        """Watch logs. Emits ``JSONL`` log data."""

        await websocket.accept()
        await cls.ws(schemas.Log, websocket, database, last=64)


class QuartoRoutes(LogRoutesMixins, base.Router):
    """View for ``quarto render`` logs.

    These logs are generated using the output from the rendering from
    ``BlogHandler``.
    """

    router = fastapi.APIRouter()
    router_routes: ClassVar[dict[str, str | dict[str, Any]]] = {
        # "post_filter": dict(url="/filter"),
        "post_log": dict(url=""),
        "get_log_status": dict(url="/status"),
        "post_last_rendered": dict(url="/last", status_code=fastapi.status.HTTP_200_OK),
        "delete_log": dict(url=""),
        "get_routes": dict(url="/routes"),
        "post_render": dict(url="/render"),
        "websocket_log": dict(url=""),
    }

    @classmethod
    async def post_last_rendered(
        cls,
        database: depends.Db,
        filters: schemas.QuartoHistoryFilters | None = None,
    ) -> schemas.QuartoHistoryMinimal | None:
        """Get the most recent qmd document rendered."""

        res = await schemas.QuartoHistoryMinimal.last_rendered(database, filters)
        if res is None:
            raise fastapi.HTTPException(204)

        return res

    @classmethod
    async def post_log(
        cls,
        database: depends.Db,
        *,
        filters: schemas.QuartoHistoryFilters | None = None,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ) -> schemas.QuartoHistoryMinimal | None:
        """Get the log for the current instance.

        This will update everytime that uvicorn reloads.
        """

        return await cls.get(  # type: ignore
            schemas.QuartoHistoryMinimal,
            database,
            do_print=True,
            slice_start=slice_start,
            slice_count=slice_count,
            filters=filters,
        )

    # @classmethod
    # async def post_filter(
    #     cls, filters: schemas.QuartoHistoryFilters
    # ) -> schemas.QuartoHistoryFilters:
    #     """Returns hydrated filter."""
    #
    #     return filters

    @classmethod
    async def post_render(
        cls,
        quarto_handler: depends.QuartoHandler,
        render_data: schemas.QuartoRenderRequest,
    ) -> schemas.QuartoRenderResponse:

        items = []
        ignored = []
        for item in render_data.items:
            data = await quarto_handler(item)
            if data is None:
                ignored.append(item)
                continue

            items.append(data)

        return schemas.QuartoRenderResponse(
            items=items,
            ignored=ignored,
        )

    @classmethod
    async def get_log_status(cls, database: depends.Db) -> schemas.LogStatus:
        """Collection status report."""

        return await cls.status(schemas.QuartoHistory, database)

    @classmethod
    async def delete_log(cls, database: depends.Db) -> int:
        """Clear all besides the current log."""

        res = await cls.delete(schemas.QuartoHistory, database)
        return res.deleted_count

    @classmethod
    async def websocket_log(
        cls,
        websocket: fastapi.WebSocket,
        database: depends.Db,
        last: int = 32,
    ):
        """Watch logs. Emits ``JSONL`` log data.

        Will not emit logs until filtering parameters are sent in.
        """

        await websocket.accept()

        # NOTE: Because a JSON body can not be sent in with the initial request
        #       the socket will wait for some filters to be written to it.
        data = await websocket.receive_json()
        if data is not None:
            try:
                filters = schemas.QuartoHistoryFilters.model_validate(data)
            except pydantic.ValidationError as err:
                # NOTE: https://github.com/Luka967/websocket-close-codes
                raise fastapi.WebSocketDisconnect(1003, err.json())
        else:
            filters = None

        await cls.ws(
            schemas.QuartoHistoryFull,
            websocket,
            database,
            filters=filters,
            last=last,
        )


class DevRoutes(base.Router):
    """Routes for development mode.

    Not included in the production application.
    """

    router = fastapi.APIRouter()
    router_children = {"/log": LogRoutes, "/quarto": QuartoRoutes}
    router_routes = dict(
        get_routes=dict(url="/routes"),
    )


class ApiRoutes(base.Router):

    router_args = dict(prefix="/api")
    router: fastapi.FastAPI = fastapi.FastAPI(**router_args)  # type: ignore
    router_routes = dict(
        get_routes=dict(url="/routes"),
        get_it_works=dict(url=""),
    )
    router_children = dict()

    if env.ENV_IS_DEV:
        router_children["/dev"] = DevRoutes
