import asyncio
import datetime
import http
import os
import pathlib
import re
from typing import Annotated, Any, ClassVar, Literal, Self

import bson
import fastapi
import motor.motor_asyncio
import pydantic

from acederbergio import db, env, util


class LogItem(pydantic.BaseModel):
    created: util.FieldTimestamp
    filename: str
    funcName: str
    levelname: str
    levelno: int
    lineno: int
    module: str
    msg: str
    name: str
    pathname: str
    threadName: str

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def created_time(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.created)


LogQuartoItemKind = Annotated[
    Literal["defered", "direct", "static"], pydantic.Field("direct")
]


class LogQuartoItem(util.HasTime):

    kind: LogQuartoItemKind
    origin: str
    target: str
    command: list[str]
    stderr: list[str]
    stdout: list[str]
    status_code: int

    @classmethod
    def removeANSIEscape(cls, v: str):
        ansi_escape = re.compile(r"\x1b\[.*?m")
        return ansi_escape.sub("", v)

    @classmethod
    async def fromProcess(
        cls,
        target: pathlib.Path,
        origin: pathlib.Path,
        process: asyncio.subprocess.Process,
        *,
        command: list[str],
        kind: LogQuartoItemKind,
    ) -> Self:
        stdout, stderr = await process.communicate()
        return cls.model_validate(
            {
                "target": str(os.path.relpath(target, env.ROOT)),
                "origin": str(os.path.relpath(origin, env.ROOT)),
                "command": command,
                "stderr": cls.removeANSIEscape(stdout.decode()).split("\n"),
                "stdout": cls.removeANSIEscape(stderr.decode()).split("\n"),
                "status_code": process.returncode,
                "kind": kind,
            }
        )


class BaseLog(util.HasTime, db.HasMongoId):
    _collection: ClassVar[str]

    count: Annotated[int, pydantic.Field(default=0)]

    @classmethod
    async def spawn(cls, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        collection = db[cls._collection]
        res = await collection.insert_one(
            {
                "timestamp": datetime.datetime.timestamp(datetime.datetime.now()),
                "items": [],
            }
        )
        return res

    @classmethod
    async def push(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        mongo_id: bson.ObjectId,
        data: list[Any],
    ):
        collection = db[cls._collection]
        res = await collection.update_one(
            {"_id": mongo_id},
            {"$push": {"items": {"$each": data}}},
        )
        return res

    @classmethod
    def aggr_latest_projection(
        cls,
        *,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ):
        if slice_start is None:
            slice = {"$slice": ["$items", slice_count]}
        else:
            slice = {"$slice": ["$items", slice_start, slice_count]}

        return {
            "_id": "$_id",
            "count": "$count",
            "timestamp": "$timestamp",
            "items": slice,
        }

    @classmethod
    def aggr_latest(
        cls,
        *,
        slice_start: int | None = None,
        slice_count: int | None = None,
    ):
        # counts = {
        #     f"count{item.title()}": {
        #         "$size": {
        #             "$filter": {
        #                 "input": "$items",
        #                 "as": "item",
        #                 "cond": {"$eq": ["$$item.kind", item]},
        #             }
        #         }
        #     }
        #     for item in ("static", "defered", "direct")
        # }
        steps = [
            {"$sort": {"timestamp": -1}},
            {"$limit": 1},
        ]

        # NOTE: Add slice counting to steps.
        if slice_count is not None:
            projection = cls.aggr_latest_projection(
                slice_start=slice_start,
                slice_count=slice_count,
            )
            steps.append({"$project": projection})

        steps.append({"$addFields": {"count": {"$size": "$items"}}})
        return steps

    @classmethod
    async def clear(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
    ):
        """Clear all log entries besides the latest."""

        collection = db[cls._collection]
        steps = cls.aggr_latest()
        steps.append({"$project": {"_id": "$_id"}})

        _ids = await collection.aggregate(steps).to_list(None)
        res = await collection.delete_many({"_ids": {"$in": _ids}})

        return res

    @classmethod
    async def latest(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        *,
        slice_start: int | None = None,
        slice_count: int | None = None,
        **kwargs,
    ):
        """Find the latest log entry."""

        collection = db[cls._collection]
        steps = cls.aggr_latest(
            slice_start=slice_start, slice_count=slice_count, **kwargs
        )

        async for item in collection.aggregate(steps):
            return item

        return None

    @classmethod
    async def status(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
    ):
        """Return document count."""

        collection = db[cls._collection]
        res = await collection.count_documents({})
        return res


# NOTE: This could be cleaned up using generics. However, fastapi does not like
#       generics so I will not be using them here.
class Log(BaseLog):
    _collection = "logs"

    items: Annotated[
        list[LogItem],
        pydantic.Field(default_factory=list),
    ]


class LogQuarto(BaseLog):
    _collection = "quarto"

    items: Annotated[
        list[LogQuartoItem],
        pydantic.Field(default_factory=list),
    ]

    @classmethod
    def aggr_latest(
        cls,
        *,
        filters: "LogQuartoFilters | None" = None,
        slice_start: int | None = None,
        slice_count: int | None = None,
        do_print: bool = False,
    ):
        pipe = super().aggr_latest(slice_start=slice_start, slice_count=slice_count)

        #  NOTE: Projections must occur separately.
        if filters is not None:
            filter = filters.projection_filter()
            pipe.insert(0, {"$project": {"items": filter}})

        if do_print:
            print(filters)
            print(pipe)

        return pipe


class LogQuartoFilters(pydantic.BaseModel):
    """Filters for document items returned.

    URL parameters will be arguments that are common to ``get`` for both
    server logs and render logs.
    """

    targets: Annotated[list[str] | None, pydantic.Field(default=None)]
    origins: Annotated[list[str] | None, pydantic.Field(default=None)]
    errors: Annotated[bool | None, pydantic.Field(default=None)]

    def projection_filter(self):
        conds: list[dict[str, Any]] = []
        if self.errors is not None:
            conds.append({"$ne" if self.errors else "$eq": ["$$item.status_code", 0]})
        if self.targets is not None:
            conds.append({"$in": ["$$item.target", self.targets]})
        if self.origins is not None:
            conds.append({"$in": ["$$item.origin", self.origins]})

        cond = {"$and": conds}
        return {"$filter": {"input": "$items", "as": "item", "cond": cond}}


class LogStatus(pydantic.BaseModel):
    count: Annotated[int, pydantic.Field(default=0)]


class BaseAppRouteInfo(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    path: Annotated[str, pydantic.Field()]
    name: Annotated[str, pydantic.Field()]


class AppRouteInfo(BaseAppRouteInfo):
    methods: Annotated[set[http.HTTPMethod], pydantic.Field()]


class AppInfo(pydantic.BaseModel):
    http: list[AppRouteInfo]
    websocket: list[BaseAppRouteInfo]
    prefix: str

    @classmethod
    def fromRouter(
        cls,
        app: fastapi.FastAPI | fastapi.APIRouter,
        *,
        prefix: str,
    ):
        websocket, http = list(), list()

        for item in app.routes:
            if isinstance(item, fastapi.routing.APIRoute):
                http.append(AppRouteInfo.model_validate(item))
                continue

            websocket.append(BaseAppRouteInfo.model_validate(item))

        return AppInfo(http=http, websocket=websocket, prefix=prefix)


class AppState(pydantic.BaseModel):
    exiting: Annotated[bool, pydantic.Field(False)]
