import asyncio
import datetime
import http
import os
import pathlib
import re
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    ClassVar,
    Generic,
    Literal,
    Self,
    TypeVar,
)

import bson
import fastapi
import motor.motor_asyncio
import pydantic
from typing_extensions import Doc

from acederbergio import db, env, util

logger = env.create_logger(__name__)


def parse_path(v: str, *, directory: bool = False) -> pathlib.Path:
    # NOTE: Handle browser paths. This should just prepend the ``blog``
    #       directory to the path, and if the path is a directory then add
    #       ``index.html``.
    if v.startswith("/") and (directory or not v.endswith(".qmd")):
        if not directory:
            v = v.replace(".html", ".qmd")
        out = pathlib.Path("./blog" + v).resolve()
    else:
        # out = pathlib.Path(v).resolve()
        out = env.WORKDIR / v

    if directory:
        return out

    return out if not out.is_dir() else (out / "index.qmd")


def create_check_items(
    relative: bool = False,
    *,
    singleton: bool = False,
    directory: bool = False,
):
    """For what should be a list of paths, resolve the list of paths and verify
    that they actually exist.

    All resolved paths should be contained within the root directory.
    """

    check_exists = os.path.isfile if not directory else os.path.isdir

    def check_items(v):
        items = list(parse_path(item) for item in v)
        if dne := tuple(filter(lambda item: not check_exists(item), items)):
            raise ValueError(f"The following paths are not files: `{dne}`.")

        if bad := tuple(item for item in items if not item.is_relative_to(env.WORKDIR)):
            raise ValueError(f"The following paths are not valid: `{bad}`.")

        if relative:
            items = list(item.relative_to(env.WORKDIR) for item in items)

        return list(str(item) for item in items)

    if not singleton:
        return pydantic.BeforeValidator(check_items)

    def check_one(v):
        out = check_items([v])

        return str(out[0])

    return pydantic.BeforeValidator(check_one)


def path_to_url(path: str, ext: str = "html"):
    """Take a path and return the url at which it should be available within
    the fastapi static mount (output of quarto render).
    """

    if path.startswith("/"):
        path = str(pathlib.Path(path).relative_to(env.WORKDIR))
        # raise ValueError("Not going to handle an absolute path.")

    parts = path.replace("./", "").split("/")
    if not parts or parts[0] != "blog":
        return None

    return ("/" + "/".join(parts[1:])).replace("qmd", ext)


UvicornUUID = Annotated[str, pydantic.Field(env.RUN_UUID)]
QuartoRenderKind = Annotated[
    Literal["defered", "direct", "static"], pydantic.Field("direct")
]
QuartoRenderFrom = Annotated[
    Literal["client", "lifespan"],
    pydantic.Field(
        alias="from",
        validation_alias=pydantic.AliasChoices("from", "item_from"),
        serialization_alias="from",
    ),
]


class LogItem(pydantic.BaseModel):
    """Server log item schema."""

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


KindHandlerResult = Annotated[
    Literal["request", "job", "render"],
    Doc(
        "This is used in ``quarto.HandlerResult`` to indicate what the "
        "handler is returning from ``__call__``."
    ),
]


class QuartoRenderJob(util.HasTime):
    """Schema for scheduled jobs.

    This should provided `scheduled_time` later on.
    """

    kind_handler_result: ClassVar[KindHandlerResult] = "job"

    item_from: QuartoRenderFrom
    kind: QuartoRenderKind
    origin: str
    target: str


# class QuartoRenderExec(QuartoRenderJob):
#     """Schema for a job currently being executed."""
#
#     kind_handler_result: ClassVar[KindHandlerResult] = "exec"
#


# TODO: Should have scheduled time, exec time, and completed time later.
class QuartoRenderMinimal(util.HasTime):
    """This should not be used internally, only to serve partial results."""

    kind_handler_result: ClassVar[KindHandlerResult] = "render"

    item_from: QuartoRenderFrom
    kind: QuartoRenderKind
    origin: str
    target: str
    status_code: int

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def target_url_path(self) -> str | None:
        return path_to_url(self.target)

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
        kind: QuartoRenderKind,
        _from: QuartoRenderFrom,
    ) -> Self:
        stdout, stderr = await process.communicate()
        return cls.model_validate(
            {
                "target": str(os.path.relpath(target, env.WORKDIR)),
                "origin": str(os.path.relpath(origin, env.WORKDIR)),
                "command": command,
                "stderr": cls.removeANSIEscape(stdout.decode()).split("\n"),
                "stdout": cls.removeANSIEscape(stderr.decode()).split("\n"),
                "status_code": process.returncode,
                "kind": kind,
                "from": _from,
            }
        )


class QuartoRender(QuartoRenderMinimal):
    command: list[str]
    stderr: list[str]
    stdout: list[str]


class BaseLog(util.HasTime, db.HasMongoId):
    _collection: ClassVar[str]

    uuid_uvicorn: UvicornUUID
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
            steps.append({"$addFields": projection})

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


T_QuartoRender = TypeVar("T_QuartoRender", bound=QuartoRenderMinimal)


class QuartoHistory(BaseLog, Generic[T_QuartoRender]):
    _collection = "quarto"

    items: Annotated[
        list[T_QuartoRender],
        pydantic.Field(default_factory=list),
    ]

    @classmethod
    def aggr_latest(
        cls,
        *,
        filters: "QuartoHistoryFilters | None" = None,
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
            filter = filters.create_filter()
            pipe.insert(2, {"$addFields": {"items": filter}})

        if do_print:
            print("filters", filters)
            print("pipe", pipe)

        return pipe

    @classmethod
    def aggr_last_rendered(cls, filters: "QuartoHistoryFilters | None" = None):

        latest = cls.aggr_latest(filters=None, include_count=False)

        if filters is not None:
            latest.insert(0, {"$addFields": {"items": filters.create_filter()}})

        latest.insert(
            1,
            {
                "$addFields": {
                    "items": {"$last": "$items"},
                    "timestamp": "$timestamp",
                    "_id": "$_id",
                    "uuid_uvicorn": "$uuid_uvicorn",
                    "count": 1,
                }
            },
        )

        latest.insert(2, {"$match": {"items": {"$exists": True}}})

        return latest

    @classmethod
    async def last_rendered(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        filters: "QuartoHistoryFilters | None" = None,
    ) -> Self | None:

        aggr = cls.aggr_last_rendered(filters)
        res = db[cls._collection].aggregate(aggr)
        async for item in res:
            item["items"] = [item["items"]]

            return cls.model_validate(item)

        return None


QuartoHistoryFull = QuartoHistory[QuartoRender]
QuartoHistoryMinimal = QuartoHistory[QuartoRenderMinimal]


class QuartoHistoryFilters(pydantic.BaseModel):
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
    kind: Annotated[list[QuartoRenderKind] | None, pydantic.Field(default=None)]

    def create_filter(self) -> dict[str, Any]:
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


class QuartoRenderRequestItem(pydantic.BaseModel):

    kind_handler_result: ClassVar[KindHandlerResult] = "request"

    kind: Annotated[Literal["file", "directory"], pydantic.Field("file")]
    path: Annotated[str, pydantic.Field()]
    directory_depth_max: Annotated[int, pydantic.Field(100, exclude=True)]

    @pydantic.model_validator(mode="before")
    def validate_path(cls, v):
        is_directory = v.get("kind") == "directory"
        path = parse_path(v["path"], directory=is_directory)
        v["path"] = str(path.relative_to(env.WORKDIR))

        tpl, msg = (
            f"`{v['path']}` is not a {{}} or does not exist (resolved to {path}).",
            None,
        )
        if is_directory and not os.path.isdir(path):
            msg = tpl.format("directory")
        elif not is_directory and not os.path.isfile(path):
            msg = tpl.format("file")

        if msg is not None:
            raise ValueError(msg)

        return v


class QuartoRenderRequest(pydantic.BaseModel):
    """Use this to request a render."""

    exit_on_failure: Annotated[bool, pydantic.Field(False)]
    items: Annotated[
        list[QuartoRenderRequestItem],
        pydantic.Field(
            description="Provide relative paths from the project root or absolute paths to browser resources.",
        ),
    ]

    @pydantic.field_validator("items", mode="before")
    def hydrate_item_from_string(cls, v):
        if not isinstance(v, list):
            return v

        return [{"path": item} if isinstance(item, str) else item for item in v]


T_QuartoRenderResponseItem = TypeVar(
    "T_QuartoRenderResponseItem", QuartoRenderMinimal, QuartoRender, QuartoRenderJob
)


class QuartoRenderResponse(pydantic.BaseModel, Generic[T_QuartoRenderResponseItem]):
    """Response from rendering."""

    uuid_uvicorn: UvicornUUID
    ignored: Annotated[list[QuartoRenderRequestItem], pydantic.Field()]
    items: Annotated[list[T_QuartoRenderResponseItem], pydantic.Field()]

    @property
    def kind_handler_result(self) -> KindHandlerResult | None:
        if not len(self.items):
            return None

        return self.items[0].kind_handler_result

    def any_failed(self) -> bool:
        if self.kind_handler_result == "job":
            return False

        return any(item.status_code != 0 for item in self.items)  # type: ignore

    def get_failed(self) -> Self:
        if self.kind_handler_result == "job":
            raise ValueError()

        items = [
            item.model_dump(mode="json") for item in self.items if item.status_code  # type: ignore
        ]

        return self.__class__(items=items, ignored=self.ignored)  # type: ignore

    @classmethod
    async def fromHandlerResults(
        cls,
        stream: AsyncGenerator["QuartoHandlerResult", None],
        callback: Callable[["QuartoHandlerResult"], Awaitable[None]] | None = None,
    ) -> Self:

        items, ignored = [], []  # type: ignore[var-annotated]
        raw = dict(items=items, ignored=ignored)  # type: ignore[var-annotated]

        async for item in stream:
            if item.kind == "request":
                ignored.append(item.data)
            else:
                items.append(item.data)

            if callback is not None:
                await callback(item)

        return cls.model_validate(raw)


T_QuartoHandlerResult = TypeVar(
    "T_QuartoHandlerResult",
    QuartoRender,
    QuartoRenderJob,
    QuartoRenderRequestItem,
)


class QuartoHandlerResult(pydantic.BaseModel, Generic[T_QuartoHandlerResult]):

    data: T_QuartoHandlerResult

    @property
    def kind(self) -> KindHandlerResult:
        return self.data.kind_handler_result


QuartoHandlerRender = QuartoHandlerResult[QuartoRender]
QuartoHandlerJob = QuartoHandlerResult[QuartoRenderJob]
QuartoHandlerRequest = QuartoHandlerResult[QuartoRenderRequestItem]
QuartoHandlerAny = QuartoHandlerRequest | QuartoHandlerJob | QuartoHandlerRender


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
