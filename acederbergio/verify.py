"""This module should contain build quality assurance and scripts. There are
a few goals here:

1. Ensure pages that previously existed still do exist.
2. Ensure pages do not drift too far from the last.
3. Execute selenium scripts to make sure that things still work.
"""

import pathlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Annotated, Any, Literal

import bson
import pydantic
import pymongo
import requests
import rich
import typer
import yaml_settings_pydantic as ysp
from pymongo.collection import Collection
from typing_extensions import Self

from acederbergio import config, db, env, util

SITEMAP_NAMESPACE = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
MONGO_COLLECTION = "metadata"
LABEL_PATTERN = re.compile("(?P<key>[a-zA-Z_*.]+)=(?P<value>[a-zA-Z_*]+)")

logger = env.create_logger(__name__)


class SiteMapURLSet(pydantic.BaseModel):
    loc: Annotated[str | None, pydantic.Field()]
    lastmod: datetime
    changefreq: Annotated[str | None, pydantic.Field(default=None)]
    priority: Annotated[float | None, pydantic.Field(lt=1, gt=0, default=None)]

    @classmethod
    def _fromXML(cls, xml: ET.Element | Any):
        raw = {
            key: value.text
            for key in cls.model_fields
            if (value := xml.find(f"ns:{key}", SITEMAP_NAMESPACE)) is not None
        }
        return raw


class SiteMap(pydantic.BaseModel):
    urlset: dict[str, SiteMapURLSet]

    @classmethod
    def fromXML(cls, xml: str):
        logger.debug("Parsing sitemap `XML`.")

        tree = ET.fromstring(xml)
        items = tree.findall("ns:url", SITEMAP_NAMESPACE)
        urlset = (SiteMapURLSet._fromXML(url) for url in items)
        return cls(urlset={item["loc"]: item for item in urlset})  # type: ignore


class Source(pydantic.BaseModel):
    name: str
    kind: Literal["test", "site", "directory"]
    site: Annotated[
        pydantic.AnyHttpUrl | None,
        pydantic.Field(default=None),
    ]
    directory: Annotated[
        pathlib.Path | None,
        pydantic.Field(default=None),
    ]

    def require_site(self) -> pydantic.AnyHttpUrl:
        if (source_site := self.site) is None:
            raise ValueError("Need site.")

        return source_site

    def require_directory(self) -> pathlib.Path:
        if (source_dir := self.directory) is None:
            raise ValueError("Need directory.")

        return source_dir

    def mongo_match(self) -> dict[str, Any]:
        # _m = self.model_dump(mode="json", exclude_none=True)
        # _m = {f"source.{key}": value for key, value in _m.items()}
        return {"source.name": self.name}

    @pydantic.model_validator(mode="before")
    def check_one_source(cls, v):

        if v.get("kind") == "test":
            return v

        source_site = v.get("site")
        source_directory = v.get("directory")
        if source_site is None and source_directory is None:
            raise ValueError(
                "At least one of ``--directory`` or ``--source_site`` is required."
            )
        if source_site is not None and source_directory is not None:
            raise ValueError("Cannot specify both of ``--directory`` and ``--site``.")

        v["kind"] = "site" if source_site is not None else "directory"

        return v

    def _get_content(self, name: str) -> str:
        if self.kind == "directory":
            with open(p := self.require_directory() / name, "r") as file:
                logger.debug("Loading `%s` from file `%s`.", name, p)
                data = file.read()

            return data
        elif self.kind == "test":
            raise ValueError(
                "`_get_content` should never be called when `kind='test'`."
                "Instead, make sure to pass `_site_map` and `_build_info` to "
                "`Handler`."
            )

        url = str(self.require_site()) + "/" + name
        logger.debug("Loading `%s` from url `%s`.", name, url)

        if (response := requests.get(url)).status_code != 200:
            rich.print(
                f"[red]Unexpected repsonse `{response.status_code}` for request to `{response.request.url}`."
            )
            raise typer.Exit(206)

        return response.content.decode()


class SourceReport(pydantic.BaseModel):
    source: Source
    count: int
    timestamp_terminal: int
    timestamp_initial: int
    build_info: config.BuildInfo

    @classmethod
    def aggr(cls, *, source_names: list[str]):
        return [
            {"$sort": {"timestamp": 1}},
            {
                "$match": {
                    "source.name": {"$in": source_names},
                },
            },
            {
                "$group": {
                    "_id": "$source.name",
                    "count": {"$count": {}},
                    "timestamp_initial": {"$min": "$timestamp"},
                    "timestamp_terminal": {"$max": "$timestamp"},
                    "source": {"$first": "$source"},
                    "build_info": {"$last": "$build_info"},
                },
            },
        ]


class Search(pydantic.BaseModel):
    source: Annotated[Source | None, pydantic.Field(default=None)]
    commit: Annotated[str | None, pydantic.Field(default=None)]
    ref: Annotated[str | None, pydantic.Field(default=None)]
    mongo_id: db.FieldObjectId

    def find(self) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if self.commit is not None:
            query["build_info.git_commit"] = self.commit
        if self.ref is not None:
            query["build_info.git_ref"] = self.ref
        if self.mongo_id is not None:
            query["_id"] = bson.ObjectId(self.mongo_id)

        if len(query) > 1:
            query = {"$or": [{k: v} for k, v in query.items()]}

        if self.source is not None:
            query.update(self.source.mongo_match())

        if len(query) == 0:
            raise ValueError("Query is empty.")

        return query

    def aggr_top(self) -> db.Aggr:

        aggr: db.Aggr = [
            {"$match": {**self.find(), "before": None}},
            {"$sort": {"timestamp": -1}},
            {
                "$project": {
                    "timestamp": "$timestamp",
                    "_id": "$_id",
                    "labels": "$labels",
                }
            },
            {"$limit": 1},
        ]

        return aggr


Labels = dict[str, int | str] | None


class Minimal(util.HasTimestamp):
    build_info: config.BuildInfo

    depth: Annotated[int | None, pydantic.Field(default=None)]
    labels: Annotated[Labels, pydantic.Field(default=None)]
    mongo_id: db.FieldObjectId
    after: db.FieldId
    before: db.FieldId


class Metadata(Minimal):
    site_map: SiteMap
    source: Source

    def minify(self) -> Minimal:
        return Minimal.model_validate(self.model_dump())

    def aggr_neighbors(self, *, exclude_self=True) -> db.Aggr:
        commit = self.build_info.git_commit
        aggr = self.source.mongo_match()
        if exclude_self:
            aggr["build_info.git_commit"] = {"$ne": commit}

        return [{"$match": aggr}, {"$sort": {"build_info.timestamp": 1}}]

    def aggr_history(self) -> db.Aggr:

        aggr = self.aggr_neighbors(exclude_self=False)
        aggr.append(self.project_min())

        return aggr

    @classmethod
    def project_min(cls):
        return {
            "$project": {
                "build_info": "$build_info",
                "before": "$before",
                "after": "$after",
                "time": "$time",
                "labels": "$labels",
            }
        }

    def updates_append(self, next: Self):
        """Append  ``next`` to the linked list."""

        return self.updates_append_ids(
            mongo_id_head=bson.ObjectId(self.mongo_id),
            mongo_id_next=bson.ObjectId(next.mongo_id),
        )

    @classmethod
    def updates_append_ids(
        cls,
        *,
        mongo_id_head: bson.ObjectId,
        mongo_id_next: bson.ObjectId,
    ):
        update_head = dict(before=mongo_id_next)
        update_next = dict(after=mongo_id_head)

        return (
            ({"_id": mongo_id_head}, {"$set": update_head}),
            ({"_id": mongo_id_next}, {"$set": update_next}),
        )

    @classmethod
    def updates_pop(cls, mongo_id_head: bson.ObjectId):
        return ({"_id": mongo_id_head}, {"$set": {"before": None}})

    @classmethod
    def aggr_linkedlist(
        cls,
        source: Source,
        *,
        depth: int | None = None,
    ):

        match = {"$match": {"before": None, **source.mongo_match()}}
        lookup = {
            "$graphLookup": {
                "from": "metadata",
                "startWith": "$after",
                "connectFromField": "after",
                "connectToField": "_id",
                "as": "items",
                "depthField": "depth",
            },
        }
        fix_depth = {
            "$addFields": {
                "items": {
                    "$map": {
                        "input": "$items",
                        "as": "item",
                        "in": {
                            "$mergeObjects": [
                                "$$item",
                                {"depth": {"$add": ["$$item.depth", 1]}},
                            ]
                        },
                    }
                }
            }
        }

        q = [match, lookup, fix_depth]
        if depth is not None:
            q.append({"$limit": depth}) # type: ignore

        return q

    @classmethod
    def aggr_linkedlist_item(
        cls,
        source: Source,
        *,
        depth: int | None = None,
    ):
        q = cls.aggr_linkedlist(source, depth=depth)
        q.append(
            {
                "$project": {
                    "_id": "$_id",
                    "found": {"$last": "$items"},
                }
            }
        )

        return q


class History(pydantic.BaseModel):
    source: Source
    items: list[Minimal]


class Handler:
    source: Source
    db_config: db.Config

    _collection_name: str
    _client: pymongo.MongoClient | None
    _site_map: SiteMap | None
    _build_info: config.BuildInfo | None
    _metadata: Metadata | None

    def __init__(
        self,
        source: Source,
        *,
        db_config: db.Config | None = None,
        _site_map: SiteMap | None = None,
        _build_info: config.BuildInfo | None = None,
        _collection_name: str = MONGO_COLLECTION,
    ):
        self.source = source
        self.db_config = db_config if db_config is not None else db.Config()  # type: ignore

        self._client = None
        self._site_map = _site_map
        self._build_info = _build_info

        self._metadata = None
        self._collection_name = _collection_name

    @property
    def client(self):
        if self._client is None:
            self._client = self.db_config.create_client()
        return self._client

    @property
    def collection(self):
        db = self.client[self.db_config.database]
        return db[self._collection_name]

    @property
    def site_map(self) -> SiteMap:

        if self._site_map is None:
            self._site_map = SiteMap.fromXML(self.source._get_content("sitemap.xml"))

        return self._site_map

    @property
    def build_info(self) -> config.BuildInfo:

        if self._build_info is None:
            self._build_info = config.BuildInfo.model_validate_json(
                self.source._get_content("build.json")
            )

        return self._build_info  # type: ignore

    def metadata(
        self,
        _time: datetime | None = None,
        labels: Labels = None,
    ) -> Metadata:
        v: dict[str, Any] = {
            "labels": labels,
            "build_info": self.build_info,
            "source": self.source,
            "site_map": self.site_map,
        }
        if _time is not None:
            v["time"] = _time
        return Metadata.model_validate(v)

    def find(self, depth: int):
        """Look back some number of entries since the top."""

        q = Metadata.aggr_linkedlist_item(self.source, depth=depth)
        res = self.collection.aggregate(q).next()

        # util.print_yaml(res)
        return Metadata.model_validate(res["found"])

    def get(
        self,
        params: Search,
    ) -> Metadata | None:

        q = params.find()
        raw = self.collection.find_one(q)
        if raw is None:
            return None
        return Metadata.model_validate(raw)

    def require(self, params: Search) -> Metadata:
        data = self.get(params)
        if data is None:
            f = params.model_dump(exclude_none=True)
            raise ValueError(f"Could not find entry mataching `params={f}`.")

        return data

    def push(
        self,
        *,
        force: bool = False,
        **metadata_args,
    ) -> bson.ObjectId | None:
        """For the specified source, check if there is already a document (via
        git commit hash from ``build.json``).

        If there is, return nothing. Otherwise return the id of the created
        document.
        """

        commit = self.build_info.git_commit
        collection = self.collection

        params = Search(commit=commit, source=self.source)  # type: ignore
        if not force and (self.get(params)) is not None:
            return None

        metadata_id_top = self.top()

        # NOTE: Add data, ensure linked list structure.
        metadata = self.metadata(**metadata_args)
        metadata_id = collection.insert_one(
            metadata.model_dump(mode="json")
        ).inserted_id

        if metadata_id_top:
            qs = Metadata.updates_append_ids(
                mongo_id_head=metadata_id_top,
                mongo_id_next=metadata_id,
            )
            collection.update_one(*qs[0])
            collection.update_one(*qs[1])

        return metadata_id

    def pop(self) -> Metadata | None:

        top = self.top()
        if top is None:
            return None

        collection = self.collection
        params = Search(_id=top, source=self.source)  # type: ignore
        removed_raw = collection.find_one(match := params.find())
        if removed_raw is None:
            raise ValueError("Top vanished.")

        # NOTE: Detach from new head.
        removed = Metadata.model_validate(removed_raw)
        if removed.after:
            q = Metadata.updates_pop(bson.ObjectId(removed.after))
            res = self.collection.update_one(*q)

        # NOTE: Delete once detached.
        res = self.collection.delete_one(match)
        if not res.acknowledged or res.raw_result["n"] != 1:
            raise ValueError(f"Database error: `{res}`.")

        return removed

    def top(self) -> bson.ObjectId | None:
        collection = self.collection
        param = Search(source=self.source)  # type: ignore
        q = param.aggr_top()
        res = tuple(collection.aggregate(q))
        if len(res) == 0:
            return None

        return res[0]["_id"]

    def diff(
        self,
        params: Search | None = None,
    ) -> dict[str, set[str]] | None:
        """For now, just look for urls that have been deleted."""

        if params is not None:
            metadata_prev = self.get(params)
            if metadata_prev is None:
                return None
        else:
            metadata_prev_id = self.top()
            if not metadata_prev_id:
                return None

            param = Search(  # type: ignore
                _id=metadata_prev_id,  # type: ignore
                source=self.source,
            )
            metadata_prev = self.require(param)

        metadata = self.metadata()
        metadata_neighbors = metadata.aggr_neighbors(exclude_self=True)

        if not len(metadata_neighbors):
            return None

        # NOTE: Check containment.
        site_map_prev = set(metadata_prev.site_map.urlset)
        site_map = set(metadata.site_map.urlset)

        return {
            "created": site_map_prev - site_map,
            "destroyed": site_map - site_map_prev,
        }

    def history(
        self,
        use_timestamp: bool = True,
    ) -> History:
        """Get history for the specified source."""

        collection = self.collection
        metadata = self.metadata()
        q = (
            metadata.aggr_history()
            if use_timestamp
            else metadata.aggr_linkedlist(self.source)
        )
        items = collection.aggregate(q)

        if not use_timestamp:
            items = items.next()["items"]
            # items.append()

        return History(items=items, source=metadata.source)  # type: ignore

    @classmethod
    def sources(cls, collection: Collection) -> list[Source]:
        """Get all sources specified within the database"""

        res = collection.aggregate(
            [
                {
                    "$group": {
                        "_id": "$source.name",
                        "source": {"$first": "$source"},
                    }
                }
            ]
        )
        return [Source.model_validate(item["source"]) for item in res]

    @classmethod
    def report(
        cls, collection: Collection, *, source_names: list[str]
    ) -> list[SourceReport]:
        q = SourceReport.aggr(source_names=source_names)
        items = collection.aggregate(q)

        return list(SourceReport.model_validate(item) for item in items)


# --------------------------------------------------------------------------- #

CONFIG = env.CONFIGS / "sources.yaml"


def print_site_metadata(res, *, full: bool):
    if res is None:
        rich.print("[red]No document found.")
        raise typer.Exit(0)

    exclude = set()
    if not full:
        exclude.add("site_map")

    util.print_yaml(res.model_dump(mode="json", exclude=exclude))


class Config(ysp.BaseYamlSettings):
    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={CONFIG: ysp.YamlFileConfigDict(required=True)},
        env_prefix=env.name("mongodb_"),
    )
    default: Annotated[str, pydantic.Field(default=None)]
    sources: Annotated[dict[str, Source], pydantic.Field(default=None)]

    @pydantic.field_validator("sources", mode="before")
    def populate_source_names(cls, v):
        if not isinstance(v, dict):
            return v

        # NOTE: Assumes that dict is JSON like.
        return {key: {**value, "name": key} for key, value in v.items()}

    @pydantic.model_validator(mode="after")
    def default_in_sources(self) -> Self:
        if self.default not in self.sources:
            raise ValueError(f"No configuration for source `{self.default}`.")

        return self

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def use(self) -> Source:
        return self.sources[self.default]


FlagLabel = Annotated[
    list[str],
    typer.Option(
        "--label",
        help="Labels for metadata. Should be specified like 'key=value'.",
    ),
]
FlagSourceNames = Annotated[
    list[str],
    typer.Option("--source", help="A list of sources."),
]
FlagSourceName = Annotated[
    str | None,
    typer.Option(
        "--source",
        help="Specify a source using its keys in ``sources.yaml``.",
    ),
]
FlagSourceSite = Annotated[
    str | None,
    typer.Option(
        "--site",
        help="Specify a using a source site. This must include the protocol.",
    ),
]
FlagSourceDirectory = Annotated[
    str | None,
    typer.Option(
        "--directory",
        "-d",
        help=(
            "Specify using a directory source. This must be a valid path in "
            "the current working directory."
        ),
    ),
]
FlagForce = Annotated[bool, typer.Option("--force/--no-force")]
FlagDepth = Annotated[int, typer.Option("--depth", "-d")]
FlagFull = Annotated[bool, typer.Option("--full/--partial")]


class ContextMetadata(pydantic.BaseModel):
    """Context for the ``site`` command."""

    source: Source

    @classmethod
    def callback(
        cls,
        context: typer.Context,
        source_name: FlagSourceName = None,
        source_site: FlagSourceSite = None,
        source_directory: FlagSourceDirectory = None,
    ):

        # NOTE: Using source explicity from CLI
        if source_site is not None or source_directory is not None:
            try:
                source = Source(  # type: ignore
                    name="typer",
                    site=source_site,  # type: ignore
                    directory=source_directory,  # type: ignore
                )
            except pydantic.ValidationError as err:

                rich.print("[red]Configuration Errors:")
                for line in err.errors():
                    rich.print(f'[red]{ line["msg"] }: {str(set(line["loc"]))}')

                raise typer.Exit(201) from err

            return
        else:
            # NOTE: Source from configuration.
            v = {}
            if source_name:
                v["default"] = source_name

            config = Config.model_validate(v)
            source = config.use

        context.obj = cls(source=source)

    def create_handler(self) -> Handler:
        return Handler(self.source)


cli = typer.Typer(
    pretty_exceptions_enable=False,
    help="Tools for verifying site integrity.",
)
sources = typer.Typer(
    help="Tools for viewing sources in the database.",
)
metadata = typer.Typer(
    callback=ContextMetadata.callback,
    help="Tools for manipulating and comparing metadata.",
)
cli.add_typer(sources, name="sources")
cli.add_typer(metadata, name="metadata")


@cli.command("config")
def metadata_config():
    """Show the sources config."""

    util.print_yaml(
        Config.model_validate({}),
        name=str(CONFIG),
        exclude_none=True,
    )


# NOTE: Would like to pass either a directory or site.
@metadata.command("push")
def metadata_push(
    _context: typer.Context,
    *,
    force: FlagForce = False,
    labels_raw: FlagLabel = list(),
    full: FlagFull = False,
):
    "Pull source data into mongodb and keep."

    labels_matched = (
        label_matched
        for label_raw in labels_raw
        if (label_matched := LABEL_PATTERN.match(label_raw)) is not None
    )

    labels = {v.group("key"): v.group("value") for v in labels_matched}
    labels.update({"typer.command": "push"})

    handler = _context.obj.create_handler()
    _id = handler.push(
        force=force,
        labels=labels,
    )

    if _id is None:
        commit = handler.build_info.git_commit
        rich.print(f"[yellow]Data already exists for commit `{commit}`.")
        raise typer.Exit(203)

    # handler.client.close
    data = handler.get(Search(_id=_id))  # type: ignore
    if data is None:
        rich.print(f"[red]Could not find object with `{_id = }`.")
        raise typer.Exit(204)

    if not full:
        data = data.minify()

    util.print_yaml(data, name="build info")
    return


@metadata.command("diff")
def metadata_diff(_context: typer.Context, commit: str):
    "Check source data against mongodb log."

    handler = _context.obj.create_handler()
    params = Search(commit=commit)  # type: ignore
    diff = handler.diff(params)
    if diff is None:
        rich.print("[yellow]No entries to compare to.")
        raise typer.Exit(202)

    rich.print(diff)
    return


@metadata.command("history")
def metadata_history(
    _context: typer.Context,
    use_timestamp: Annotated[
        bool,
        typer.Option("--timestamp/--linked-list"),
    ] = True,
):
    """Show metadata history."""

    handler = _context.obj.create_handler()
    res = handler.history(use_timestamp=use_timestamp)
    util.print_yaml(res.model_dump(mode="json"), name="history")

    return


@metadata.command("top")
def metadata_top(
    _context: typer.Context,
    full: FlagFull = False,
):
    """Show the most recent metadata."""

    handler = _context.obj.create_handler()

    if (_id := handler.top()) is None:
        rich.print("[red]No data for source.")
        return

    res = handler.get(Search(_id=_id))  # type: ignore
    print_site_metadata(res, full=full)


@metadata.command("pop")
def metadata_pop(
    _context: typer.Context,
    full: FlagFull = False,
):
    """Remove the most recent metadata."""

    handler = _context.obj.create_handler()
    res = handler.pop()
    if not full:
        res = res.minify()
    util.print_yaml(res)

    return


@metadata.command("get")
def metadata_get(
    _context: typer.Context,
    commit: str | None = None,
    ref: str | None = None,
    _id: str | None = None,
    full: FlagFull = False,
):
    """Get metadata from mongodb."""

    handler = _context.obj.create_handler()
    params = Search(
        commit=commit,
        ref=ref,
        _id=_id,  # type: ignore
        source=handler.source,
    )
    res = handler.get(params)
    print_site_metadata(res, full=full)


@metadata.command("find")
def metadata_find(
    _context: typer.Context,
    *,
    depth: FlagDepth,
    full: FlagFull = False,
):
    """Find an entry ``--depth`` far back."""

    handler = _context.obj.create_handler()
    res = handler.find(depth)
    print_site_metadata(res, full=full)


@metadata.command("show")
def metadata_show(_context: typer.Context, full: FlagFull = False):
    """Show metadata built from source."""

    handler = _context.obj.create_handler()
    metadata = handler.metadata()
    if not full:

        metadata = pydantic.TypeAdapter(Minimal).validate_python(metadata.model_dump())
    util.print_yaml(metadata.model_dump(), name="metadata")


@sources.command("show")
def sources_show():
    """Show all sources existing in database."""
    db_config = db.Config.model_validate({})
    client = db_config.create_client()
    collection = client[db_config.database][MONGO_COLLECTION]

    util.print_yaml(
        Handler.sources(collection),
        items=True,
        name="sources",
        exclude_none=True,
    )


@sources.command("report")
def sources_report(source_names: FlagSourceNames = list()):
    "Report for a source."

    if not len(source_names):
        rich.print("[red]At least one source is required.")
        raise typer.Exit(207)
    db_config = db.Config.model_validate({})
    client = db_config.create_client()
    collection = client[db_config.database][MONGO_COLLECTION]

    util.print_yaml(
        Handler.report(collection, source_names=source_names),
        items=True,
        exclude_none=True,
    )
