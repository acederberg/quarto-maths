import asyncio
from typing import TypeVar

import fastapi
import fastapi.routing

from acederbergio import env
from acederbergio.api import base, depends, schemas

logger = env.create_logger(__name__)

T_BaseLog = TypeVar("T_BaseLog", bound=schemas.BaseLog)


class LogRoutesMixins:
    """Generics help write less code in a way that type hints are happy.

    The problem is that ``fastapi`` does not resolve the annotations, so children
    will provide wrappers with annotations that ``fastapi`` will find okay.
    """

    router_routes = {
        "get_log": dict(url=""),
        "get_log_status": dict(url="/status"),
        "delete_log": dict(url=""),
        "get_routes": dict(url="/routes"),
        "websocket_log": dict(url=""),
    }

    @classmethod
    async def get(cls, s: type[T_BaseLog], database: depends.Db, **kwargs) -> T_BaseLog:

        data = await s.latest(database, **kwargs)
        if data is None:
            raise fastapi.HTTPException(204, detail={"msg": "No log data found."})

        return s.model_validate(data)

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
    ):
        await websocket.accept()

        # NOTE: Push out the initial logs.
        log = await cls.get(s, database)
        await websocket.send_text(log.model_dump_json())

        count = log.count

        while True:
            await asyncio.sleep(1)

            data = await cls.get(s, database, slice_start=count, slice_count=128)
            if not data.count:
                continue

            await websocket.send_text(data.model_dump_json(indent=2))
            count += data.count


# TODO: Make router generic.
class LogRoutes(LogRoutesMixins, base.Router):
    """View fastapi logs in dev application.

    Logs are first written into a unix socket in ``dev.Watcher`` and then
    pushed to mongodb.
    """

    router = fastapi.APIRouter()

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
        return await cls.get(
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
    async def delete_log(cls, database: depends.Db) -> None:
        """Clear all besides the current log."""

        await cls.delete(schemas.Log, database)

    @classmethod
    async def websocket_log(
        cls,
        websocket: fastapi.WebSocket,
        database: depends.Db,
    ):
        """Watch logs. Emits ``JSONL`` log data."""

        await cls.ws(schemas.Log, websocket, database)


class QuartoRoutes(LogRoutesMixins, base.Router):
    """View for ``quarto render`` logs.

    These logs are generated using the output from the rendering from
    ``BlogHandler``.
    """

    router = fastapi.APIRouter()

    @classmethod
    async def get_log(
        cls,
        database: depends.Db,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ) -> schemas.LogQuarto:
        """Get the log for the current instance.

        This will update everytime that uvicorn reloads.
        """
        return await cls.get(
            schemas.LogQuarto,
            database,
            slice_start=slice_start,
            slice_count=slice_count,
        )

    @classmethod
    async def get_log_status(cls, database: depends.Db) -> schemas.LogStatus:
        """Collection status report."""

        return await cls.status(schemas.LogQuarto, database)

    @classmethod
    async def delete_log(cls, database: depends.Db) -> None:
        """Clear all besides the current log."""

        await cls.status(schemas.LogQuarto, database)

    @classmethod
    async def websocket_log(
        cls,
        websocket: fastapi.WebSocket,
        database: depends.Db,
    ):
        """Watch logs. Emits ``JSONL`` log data."""

        await cls.ws(schemas.LogQuarto, websocket, database)


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
