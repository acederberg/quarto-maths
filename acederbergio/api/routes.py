from typing import Any

import fastapi

from acederbergio import env
from acederbergio.api import base, depends, schemas


# TODO: Make router generic.
class LogRoutes(base.Router):
    """View fastapi logs in dev application.

    Logs are first written into a unix socket in ``dev.Watcher`` and then
    pushed to mongodb.
    """

    router_routes = {
        "get_log": dict(url=""),
        # "stream_log": "/log",
    }

    @classmethod
    async def get_log(
        cls,
        client: depends.DbClient,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ) -> schemas.LogSchema:
        """Look for the most recent log data."""

        collection = client["logs"]
        steps = [
            {"$sort": {"timestamp": -1}},
            {"$limit": 1},
            {"$addFields": {"count": {"$size": "$items"}}},
        ]

        # NOTE: Add slice counting to steps.
        if slice_count is not None:
            if slice_start is None:
                slice = {"$slice": ["$items", slice_count]}
            else:
                slice = {"$slice": ["$items", slice_start, slice_count]}

            projection = {
                "_id": "$_id",
                "count": "$count",
                "timestamp": "$timestamp",
                "items": slice,
            }
            steps.insert(-1, {"$project": projection})
        elif slice_start is not None:
            raise fastapi.HTTPException(
                422,
                detail={
                    "msg": "`slice_start` may only be specified when `slice_count` is specified."
                },
            )

        print(collection)
        res = collection.aggregate(steps)
        data = await res.next()
        if data is None:
            raise fastapi.HTTPException(204, detail={"msg": "No log data found."})

        return schemas.LogSchema.model_validate(
            {
                "timestamp": data["timestamp"],
                "count": data["count"],
                "items": data["items"],
                "_id": str(data["_id"]),
            }
        )

    # @classmethod
    # async def get_quarto(cls, client: depends.DbClient) -> schemas.LogSchemaQuarto:
    #     return

    # TODO: BaseRouter needs to add logs.
    # @classmethod
    # async def watch_log(
    #     cls,
    #     websocket: fastapi.WebSocket,
    #     client: depends.DbClient,
    # ):
    #
    #     log = cls.get_log(client)
    #     await websocket.send(log)
    #
    #     _id = log["_id"]
    #     count = len(log["items"])
    #     collection = client["logs"]
    #
    #     while True:
    #         res = collection.find_one(
    #             {"_id": _id},
    #             {"items": {"$slice": [count - 1, -1]}},
    #         )
    #         if res is None:
    #             continue
    #
    #         new = res["items"]
    #         yield new
    #         count += len(new)


class DevRoutes(base.Router):
    router = fastapi.APIRouter()
    router_routes = {}
    router_children = {"/log": LogRoutes}


class AppRoute(base.Router):

    router: fastapi.FastAPI = fastapi.FastAPI()  # type: ignore
    router_children = {}

    if env.ENV_IS_DEV:
        router_children["/dev"] = DevRoutes
