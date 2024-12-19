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
LogQuartoItemFrom = Annotated[
    Literal["client", "lifespan"],
    pydantic.Field(
        alias="from",
        validation_alias=pydantic.AliasChoices("from", "item_from"),
        serialization_alias="from",
    ),
]


class LogQuartoItem(util.HasTime):

    item_from: LogQuartoItemFrom
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
        _from: LogQuartoItemFrom,
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
                "from": _from,
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
        include_count: bool = True,
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

        if include_count:
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

        _id_no_rm = await collection.aggregate(steps).to_list(None)
        res = await collection.delete_many({"_id": {"$not": {"$eq": _id_no_rm}}})

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
            return cls.model_validate(item)

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
        include_count: bool = True,
        do_print: bool = False,
    ):
        pipe = super().aggr_latest(
            slice_start=slice_start,
            slice_count=slice_count,
            include_count=include_count,
        )

        #  NOTE: Projections must occur separately.
        if filters is not None:
            filter = filters.projection_filter()
            pipe.insert(2, {"$project": {"items": filter}})

        if do_print:
            print(filters)
            print(pipe)

        return pipe

    @classmethod
    def aggr_last_rendered(cls, filters: "LogQuartoFilters | None" = None):

        latest = cls.aggr_latest(filters=None, include_count=False)

        if filters is not None:
            project = {"$project": {"items": filters.projection_filter()}}
            latest.insert(0, project)

        latest.insert(
            1,
            {
                "$project": {
                    "last": {"$last": "$items"},
                    "timestamp": "$timestamp",
                }
            },
        )
        latest.insert(2, {"$match": {"last": {"$exists": True}}})
        return latest

    @classmethod
    async def last_rendered(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        filters: "LogQuartoFilters | None" = None,
    ) -> LogQuartoItem | None:

        aggr = cls.aggr_last_rendered(filters)
        res = db[cls._collection].aggregate(aggr)
        async for item in res:
            return LogQuartoItem.model_validate(item["last"])

        return None


def parse_path(v: str) -> pathlib.Path:
    # NOTE: Handle browser paths. This should just prepend the ``blog``
    #       directory to the path, and if the path is a directory then add
    #       ``index.html``.
    if v.startswith("/") and not v.endswith(".qmd"):
        v = v.replace(".html", ".qmd")
        out = pathlib.Path("./blog" + v).resolve()
    else:
        out = pathlib.Path(v).resolve()

    return out if not out.is_dir() else (out / "index.qmd")


def create_check_items(relative: bool = False):
    """For what should be a list of paths, resolve the list of paths and verify
    that they actually exist.

    All resolved paths should be contained within the root directory.
    """

    def check_items(v):
        items = list(parse_path(item) for item in v)
        if dne := tuple(filter(lambda item: not os.path.isfile(item), items)):
            raise ValueError(f"The following paths are not files: `{dne}`.")

        if bad := tuple(item for item in items if not item.is_relative_to(env.ROOT)):
            raise ValueError(f"The following paths are not valid: `{bad}`.")

        if relative:
            items = list(item.relative_to(env.ROOT) for item in items)

        return list(str(item) for item in items)

    return pydantic.BeforeValidator(check_items)


class LogQuartoFilters(pydantic.BaseModel):
    """Filters for document items returned.

    URL parameters will be arguments that are common to ``get`` for both
    server logs and render logs.
    """

    targets: Annotated[
        list[str] | None,
        pydantic.Field(default=None),
        create_check_items(relative=True),
    ]
    origins: Annotated[
        list[str] | None,
        pydantic.Field(default=None),
        create_check_items(relative=True),
    ]
    errors: Annotated[
        bool | None,
        pydantic.Field(default=None),
    ]
    kind: Annotated[list[LogQuartoItemKind] | None, pydantic.Field(default=None)]

    def projection_filter(self):
        conds: list[dict[str, Any]] = []
        if self.errors is not None:
            conds.append({"$ne" if self.errors else "$eq": ["$$item.status_code", 0]})
        if self.targets is not None:
            conds.append({"$in": ["$$item.target", self.targets]})
        if self.origins is not None:
            conds.append({"$in": ["$$item.origin", self.origins]})
        if self.kind is not None:
            conds.append({"$in": ["$$item.kind", self.kind]})

        cond = {"$and": conds}
        return {"$filter": {"input": "$items", "as": "item", "cond": cond}}


class QuartoRender(pydantic.BaseModel):
    items: Annotated[
        list[str],
        pydantic.Field(
            default_factory=list,
            description="Provide relative paths from the project root or absolute paths to browser resources.",
        ),
        create_check_items(relative=False),
    ]


class QuartoRenderResult(pydantic.BaseModel):
    ignored: Annotated[list[str], pydantic.Field()]
    items: Annotated[list[LogQuartoItem], pydantic.Field()]


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
