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

from acederbergio import config, db, env, util

SITEMAP_NAMESPACE = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
MONGO_COLLECTION = "siteMetadata"


class SiteMapURLSet(pydantic.BaseModel):
    loc: str
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
        tree = ET.fromstring(xml)
        items = tree.findall("ns:url", SITEMAP_NAMESPACE)
        urlset = (SiteMapURLSet._fromXML(url) for url in items)
        return cls(urlset={item["loc"]: item for item in urlset})  # type: ignore


class SiteSource(pydantic.BaseModel):
    kind: Literal["site", "directory"]
    site: Annotated[
        pydantic.AnyHttpUrl | None,
        pydantic.Field(default=None),
    ]
    directory: Annotated[
        pathlib.Path | None,
        pydantic.Field(default=None),
    ]

    def mongo_match(self) -> dict[str, Any]:
        _m = self.model_dump(mode="json", exclude_none=True)
        _m = {f"source.{key}": value for key, value in _m.items()}
        return _m

    @pydantic.model_validator(mode="before")
    def check_one_source(cls, v):

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


# class ListingItem(pydantic.BaseModel):
#
#     items: list[pathlib.Path]
#     listing: pathlib.Path
#
#
# Listings = list[ListingItem]


class SiteMetadataSearch(pydantic.BaseModel):
    source: Annotated[SiteSource | None, pydantic.Field(default=None)]
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
            query["_id"] = self.mongo_id

        if len(query) > 1:
            query = {"$or": [{k: v} for k, v in query.items()]}

        if self.source is not None:
            query.update(self.source.mongo_match())

        if len(query) == 0:
            raise ValueError("Query is empty.")

        return query

    def aggr_top(self) -> db.Aggr:

        aggr: db.Aggr = [{"$match": self.find()}]
        aggr.append(
            {
                "$group": {
                    "timestamp": {"$max": "$timestamp"},
                    "_id": "$build_info.git_commit",
                }
            }
        )
        aggr.append({"$limit": 1})
        aggr.append({"$project": {"building_info": "$build_info"}})
        print(aggr)

        return aggr


class SiteMetadata(util.HasTimestamp):
    build_info: config.BuildInfo
    site_map: SiteMap
    source: SiteSource

    def aggr_neighbors(self, *, exclude_self=True) -> db.Aggr:
        commit = self.build_info.git_commit
        aggr = self.source.mongo_match()
        if exclude_self:
            aggr["build_info.git_commit"] = {"$ne": commit}

        return [{"$match": aggr}, {"$sort": {"build_info.timestamp": 1}}]

    def aggr_history(self) -> db.Aggr:

        aggr = self.aggr_neighbors(exclude_self=False)
        aggr.append({"$project": {"build_info": "$build_info"}})

        return aggr


class SiteMetadataHistory(pydantic.BaseModel):

    source: SiteSource
    builds: list[config.BuildInfo]


class SiteMetdataHandler:
    context: "ContextSite"
    _client: pymongo.MongoClient | None
    # _listings: Listings | None
    _site_map: SiteMap | None
    _build_info: config.BuildInfo | None
    _metadata: SiteMetadata | None

    def __init__(self, context: "ContextSite"):
        self.context = context
        self._client = None
        # self._listings = None
        self._site_map = None
        self._build_info = None
        self._metadata = None

    def _get_content(self, name: str) -> str:
        if self.context.source.kind == "directory":
            with open(self.context.require_directory() / name, "r") as file:
                data = file.read()

            return data

        response = requests.get(str(self.context.require_site()) + "/" + name)
        if response.status_code != 200:
            rich.print(
                f"[red]Unexpected repsonse `{response.status_code}` for request to `{response.request.url}`."
            )
            raise typer.Exit()

        return response.content.decode()

    @property
    def client(self):
        if self._client is None:
            self._client = db.create_client(_mongodb_url=str(self.context.mongodb_url))
        return self._client

    @property
    def collection(self):
        db = self.client["acederbergio"]
        return db[MONGO_COLLECTION]

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
            self._site_map = SiteMap.fromXML(self._get_content("sitemap.xml"))

        return self._site_map

    @property
    def build_info(self) -> config.BuildInfo:

        if self._build_info is None:
            self._build_info = config.BuildInfo.model_validate_json(
                self._get_content("build.json")
            )

        return self._build_info  # type: ignore

    @property
    def metadata(self) -> SiteMetadata:
        if self._metadata is None:
            self._metadata = SiteMetadata.model_validate(
                {
                    "build_info": self.build_info,
                    "source": self.context.source,
                    "site_map": self.site_map,
                }
            )

        return self._metadata

    def get(
        self,
        params: SiteMetadataSearch,
    ) -> SiteMetadata | None:

        q = params.find()
        raw = self.collection.find_one(q)
        if raw is None:
            return None
        return SiteMetadata.model_validate(raw)

    def require(self, params: SiteMetadataSearch) -> SiteMetadata:
        data = self.get(params)
        if data is None:
            f = params.model_dump(exclude_none=True)
            raise ValueError(f"Could not find entry mataching `params={f}`.")

        return data

    def push(self, *, force: bool = False) -> bson.ObjectId | None:
        """For the specified source, check if there is already a document (via
        git commit hash from ``build.json``).

        If there is, return nothing. Otherwise return the id of the created
        document.
        """

        commit = self.build_info.git_commit
        collection = self.collection

        params = SiteMetadataSearch(commit=commit, source=self.context.source)  # type: ignore
        if not force and (self.get(params)) is not None:
            return

        return collection.insert_one(self.metadata.model_dump(mode="json")).inserted_id

    def top(self) -> bson.ObjectId | None:
        collection = self.collection
        param = SiteMetadataSearch(source=self.context.source)  # type: ignore
        res = collection.aggregate(param.aggr_top()).next()
        return res["_id"]

    def diff(
        self,
        params: SiteMetadataSearch | None = None,
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

            param = SiteMetadataSearch(  # type: ignore
                commit=metadata_prev_commit,
                source=self.context.source,
            )
            metadata_prev = self.require(param)

        metadata = self.metadata
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

    def history(self) -> SiteMetadataHistory:
        """Get history for the specified source."""

        collection = self.collection
        metadata = self.metadata
        history = metadata.aggr_history()
        res = map(
            lambda item: item["build_info"],
            collection.aggregate(history),
        )

        return SiteMetadataHistory(
            builds=res,  # type:ignore
            source=metadata.source,
        )


FlagSourceSite = Annotated[str | None, typer.Option("--site")]
FlagSourceDirectory = Annotated[str | None, typer.Option("--directory", "-d")]
FlagMongodbURL = Annotated[str | None, typer.Option("--mongodb-url")]
FlagForce = Annotated[bool, typer.Option("--force/--no-force")]


class ContextSite(pydantic.BaseModel):
    """Context for the ``site`` command."""

    source: SiteSource
    mongodb_url: Annotated[
        pydantic.MongoDsn,
        pydantic.Field(),
    ]

    def require_site(self) -> pydantic.AnyHttpUrl:
        if (source_site := self.source.site) is None:
            raise ValueError("Need site.")

        return source_site

    def require_directory(self) -> pathlib.Path:
        if (source_dir := self.source.directory) is None:
            raise ValueError("Need directory.")

        return source_dir

    @pydantic.model_validator(mode="before")
    def check_mongodb(cls, v):
        v["mongodb_url"] = v.get("mongodb_url") or env.get("mongodb_url")
        return v

    @classmethod
    def callback(
        cls,
        context: typer.Context,
        _mongodb_url: FlagMongodbURL = None,
        source_site: FlagSourceSite = None,
        source_directory: FlagSourceDirectory = None,
    ):
        try:
            context.obj = ContextSite(  # type:ignore
                mongodb_url=_mongodb_url,  # type: ignore
                source=dict(site=source_site, directory=source_directory),  # type: ignore
            )
        except pydantic.ValidationError as err:

            for line in err.errors():
                rich.print(f'[red]{ line["msg"] }: {str(set(line["loc"]))}')

            raise typer.Exit(201) from err


cli = typer.Typer(pretty_exceptions_enable=False)
site = typer.Typer(callback=ContextSite.callback, pretty_exceptions_enable=False)

cli.add_typer(site, name="site")


# NOTE: Would like to pass either a directory or site.
@site.command("push")
def metadata_append(_context: typer.Context, *, force: FlagForce = False):
    "Pull source data into mongodb and keep."
    handler = SiteMetdataHandler(_context.obj)
    _id = handler.push(force=force)

    if _id is None:
        commit = handler.build_info.git_commit
        rich.print(f"[yellow]Data already exists for commit `{commit}`.")
        raise typer.Exit(203)

    data = handler.get(SiteMetadataSearch(_id=_id))  # type: ignore
    assert data is not None
    util.print_yaml(data["build_info"], name="build info")
    return


@site.command("diff")
def metadata_diff(_context: typer.Context, commit: str):
    "Check source data against mongodb log."
    handler = SiteMetdataHandler(_context.obj)
    params = SiteMetadataSearch(commit=commit)  # type: ignore
    diff = handler.diff(params)
    if diff is None:
        rich.print("[yellow]No entries to compare to.")
        raise typer.Exit(202)

    rich.print(diff)
    return


@site.command("history")
def metadata_history(_context: typer.Context):
    handler = SiteMetdataHandler(_context.obj)
    res = handler.history()
    util.print_yaml(res.model_dump(mode="json"), name="history")

    return


@site.command("top")
def metadata_top(
    _context: typer.Context,
    full: bool = False,
):
    handler = SiteMetdataHandler(_context.obj)
    commit = handler.top()
    res = handler.get(SiteMetadataSearch(commit=commit))  # type: ignore

    print_site_metadata(res, full=full)


@site.command("get")
def metadata_get(
    _context: typer.Context,
    commit: str | None = None,
    ref: str | None = None,
    _id: str | None = None,
    full: bool = False,
):
    handler = SiteMetdataHandler(_context.obj)
    params = SiteMetadataSearch(
        commit=commit,
        ref=ref,
        _id=_id,  # type: ignore
        source=handler.context.source,
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
    handler = SiteMetdataHandler(_context.obj)
    util.print_yaml(handler.metadata.model_dump(), name="metadata")


@cli.command("ping")
def ping(_mongodb_url: FlagMongodbURL = None):
    db.check_client(_mongodb_url)
