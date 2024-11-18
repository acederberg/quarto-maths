"""This module should contain build quality assurance and scripts. There are
a few goals here:

1. Ensure pages that previously existed still do exist.
2. Ensure pages do not drift too far from the last.
3. Execute selenium scripts to make sure that things still work.
"""

import pathlib
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Annotated, Any, Literal

import bson
import pydantic
import pymongo
import requests
import rich
import typer
from pymongo.results import DeleteResult
from typing_extensions import Self

from acederbergio import config, db, env, util

SITEMAP_NAMESPACE = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
MONGO_COLLECTION = "metadata"

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
        _m = self.model_dump(mode="json", exclude_none=True)
        _m = {f"source.{key}": value for key, value in _m.items()}
        return _m

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


# class ListingItem(pydantic.BaseModel):
#
#     items: list[pathlib.Path]
#     listing: pathlib.Path
#
#
# Listings = list[ListingItem]


class Search(pydantic.BaseModel):
    source: Annotated[Source | None, pydantic.Field(default=None)]
    commit: Annotated[str | None, pydantic.Field(default=None)]
    ref: Annotated[str | None, pydantic.Field(default=None)]
    mongo_id: db.FieldObjectId

    def find(self) -> dict[str, Any]:
        query = {}
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
    # Structure attributes
    build_info: config.BuildInfo

    labels: Annotated[Labels, pydantic.Field(default=None)]
    mongo_id: db.FieldObjectId
    after: db.FieldId
    before: db.FieldId


class Metadata(Minimal):
    site_map: SiteMap
    source: Source

    def aggr_neighbors(self, *, exclude_self=True) -> db.Aggr:
        commit = self.build_info.git_commit
        aggr = self.source.mongo_match()
        if exclude_self:
            aggr["build_info.git_commit"] = {"$ne": commit}

        return [{"$match": aggr}, {"$sort": {"build_info.timestamp": 1}}]

    def aggr_history(self) -> db.Aggr:

        aggr = self.aggr_neighbors(exclude_self=False)
        aggr.append(
            {
                "$project": {
                    "build_info": "$build_info",
                    "before": "$before",
                    "after": "$after",
                    "time": "$time",
                    "labels": "$labels",
                }
            }
        )

        return aggr

    def updates_append(self, next: Self):
        """Append  ``next`` to the linked list."""

        head = self

        update_head = dict(before=next.mongo_id)
        update_next = dict(after=head.mongo_id)

        return (
            ({"_id": bson.ObjectId(head.mongo_id)}, {"$set": update_head}),
            ({"_id": bson.ObjectId(next.mongo_id)}, {"$set": update_next}),
        )

    # def aggr_position(self):
    #     return [
    #         {"$match": {"_id": bson.ObjectId(self.mongo_id)}},
    #         {"$project": {"before": "$before", "after": "$after"}},
    #         {"$limit": 1},
    #     ]

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

    # @property
    # def listings(self) -> Listings:
    #     if self._listings is None:
    #         self._listings = pydantic.TypeAdapter(Listings).validate_json(
    #             self.get_content("listings.json")
    #         )
    #
    #     return self._listings

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
        v = {
            "labels": labels,
            "build_info": self.build_info,
            "source": self.source,
            "site_map": self.site_map,
        }
        if _time is not None:
            v["time"] = _time
        return Metadata.model_validate(v)

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
        print("params", params.model_dump(mode="json"))
        if not force and (self.get(params)) is not None:
            return

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
            metadata_prev_commit = self.top()
            if not metadata_prev_commit:
                return None

            param = Search(  # type: ignore
                commit=metadata_prev_commit,
                source=self.source,
            )
            metadata_prev = self.require(param)

        metadata = self.metadata()
        metadata_neighbors = metadata.aggr_neighbors(exclude_self=True)

        if not len(metadata_neighbors):
            return

        # NOTE: Check containment.
        site_map_prev = set(metadata_prev.site_map.urlset)
        site_map = set(metadata.site_map.urlset)

        return {
            "created": site_map_prev - site_map,
            "destroyed": site_map - site_map_prev,
        }

    def history(self) -> History:
        """Get history for the specified source."""

        collection = self.collection
        metadata = self.metadata()
        q = metadata.aggr_history()
        items = collection.aggregate(q)

        return History(
            items=items,  # type: ignore
            source=metadata.source,
        )


FlagSourceSite = Annotated[str | None, typer.Option("--site")]
FlagSourceDirectory = Annotated[str | None, typer.Option("--directory", "-d")]
FlagForce = Annotated[bool, typer.Option("--force/--no-force")]


class Context(pydantic.BaseModel):
    """Context for the ``site`` command."""

    source: Source

    @classmethod
    def callback(
        cls,
        context: typer.Context,
        source_site: FlagSourceSite = None,
        source_directory: FlagSourceDirectory = None,
    ):
        try:
            context.obj = Context(
                mongodb=db.Config(),  # type:ignore
                source=dict(site=source_site, directory=source_directory),  # type: ignore
            )
        except pydantic.ValidationError as err:

            rich.print("[red]Configuration Errors:")
            for line in err.errors():
                rich.print(f'[red]{ line["msg"] }: {str(set(line["loc"]))}')

            raise typer.Exit(201) from err

    def create_handler(self) -> Handler:
        return Handler(self.source)


cli = typer.Typer(pretty_exceptions_enable=False)
site = typer.Typer(callback=Context.callback, pretty_exceptions_enable=False)

cli.add_typer(site, name="site")


# NOTE: Would like to pass either a directory or site.
@site.command("push")
def metadata_append(_context: typer.Context, *, force: FlagForce = False):
    "Pull source data into mongodb and keep."
    handler = _context.obj.create_handler()
    _id = handler.push(force=force)

    if _id is None:
        commit = handler.build_info.git_commit
        rich.print(f"[yellow]Data already exists for commit `{commit}`.")
        raise typer.Exit(203)

    # handler.client.close
    data = handler.get(Search(_id=_id))  # type: ignore
    if data is None:
        rich.print(f"[red]Could not find object with `{_id = }`.")
        raise typer.Exit(204)

    util.print_yaml(data.build_info.model_dump(mode="json"), name="build info")
    return


@site.command("diff")
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


@site.command("history")
def metadata_history(_context: typer.Context):
    handler = _context.obj.create_handler()
    res = handler.history()
    util.print_yaml(res.model_dump(mode="json"), name="history")

    return


@site.command("top")
def metadata_top(
    _context: typer.Context,
    full: bool = False,
):
    handler = _context.obj.create_handler()

    if (_id := handler.top()) is None:
        rich.print("[red]No data for source.")
        return

    res = handler.get(Search(_id=_id))  # type: ignore
    print_site_metadata(res, full=full)


@site.command("pop")
def metadata_pop(_context: typer.Context):
    handler = _context.obj.create_handler()
    res = handler.pop()
    util.print_yaml(res)

    return


@site.command("get")
def metadata_get(
    _context: typer.Context,
    commit: str | None = None,
    ref: str | None = None,
    _id: str | None = None,
    full: bool = False,
):
    handler = _context.obj.create_handler()
    params = Search(
        commit=commit,
        ref=ref,
        _id=_id,  # type: ignore
        source=handler.source,
    )
    res = handler.get(params)
    print_site_metadata(res, full=full)


def print_site_metadata(res, *, full: bool):
    if res is None:
        rich.print("[red]No document found.")
        raise typer.Exit(0)

    exclude = set()
    if not full:
        exclude.add("site_map")

    util.print_yaml(res.model_dump(mode="json", exclude=exclude))


@site.command("show")
def metadata_show(_context: typer.Context):
    handler = _context.obj.create_handler()
    util.print_yaml(handler.metadata().model_dump(), name="metadata")
