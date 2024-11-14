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


class SiteMetadataMongo(util.HasTimestamp):
    build_info: config.BuildInfo
    site_map: SiteMap


class SiteMetdataHandler:
    context: "ContextSite"
    _client: pymongo.MongoClient | None
    # _listings: Listings | None
    _sitemap: SiteMap | None
    _buildinfo: config.BuildInfo | None

    def __init__(self, context: "ContextSite"):
        self.context = context
        self._client = None
        # self._listings = None
        self._sitemap = None
        self._buildinfo = None

    @property
    def client(self):
        if self._client is None:
            self._client = db.create_client(_mongodb_url=str(self.context.mongodb_url))
        return self._client

    @property
    def collection(self):
        db = self.client["acederbergio"]
        return db.sitemaps

    # @property
    # def listings(self) -> Listings:
    #     if self._listings is None:
    #         self._listings = pydantic.TypeAdapter(Listings).validate_json(
    #             self.get_content("listings.json")
    #         )
    #
    #     return self._listings

    @property
    def sitemap(self) -> SiteMap:

        if self._sitemap is None:
            self._sitemap = SiteMap.fromXML(self._get_content("sitemap.xml"))

        return self._sitemap

    @property
    def buildinfo(self) -> config.BuildInfo:

        if self._buildinfo is None:
            self._buildinfo = config.BuildInfo.model_validate_json(
                self._get_content("build.json")
            )

        return self._buildinfo  # type: ignore

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

    def __call__(self) -> SiteMetadataMongo:
        return SiteMetadataMongo.model_validate(
            {
                "build_info": self.buildinfo,
                "source": self.context.source,
                "site_map": self.sitemap,
            }
        )

    def get(
        self,
        *,
        commit: str | None = None,
        ref: str | None = None,
        _id: bson.ObjectId | None = None,
    ):
        collection = self.collection
        query = {}
        if commit is not None:
            query["build_info.git_commit"] = commit
        if ref is not None:
            query["build_info.git_ref"] = commit
        if _id is not None:
            query["_id"] = _id

        if len(query) == 0:
            raise ValueError("Query is empty.")
        elif len(query) != 1:
            query = {"$or": [{k: v} for k, v in query.items()]}

        print(query)
        return collection.find_one(query)

    def push(self, *, force: bool = False) -> bson.ObjectId | None:
        commit = self.buildinfo.git_commit
        collection = self.collection

        if not force and self.get(commit=commit):
            return

        return collection.insert_one(self().model_dump(mode="json")).inserted_id

    def test(self):
        """For now, just look for urls that have been deleted."""

        collection = self.collection

        commit = self.buildinfo.git_commit
        _m = self.context.source.model_dump(mode="json", exclude_none=True)
        _m = {f"source.{key}": value for key, value in _m.items()}
        _m["build_info.git_commit"] = {"$ne": commit}
        if collection.count_documents(_m) <= 1:
            return

        _g = {
            "timestamp": {"$max": "$timestamp"},
            "_id": "$build_info.git_commit",
        }
        commit_prev_query = [{"$match": _m}, {"$group": _g}]
        commit_prev = collection.aggregate(commit_prev_query).next()["_id"]

        if (prev := self.get(commit=commit_prev)) is None:
            raise ValueError(f"Could not find entry for commit `{commit}`.")

        # NOTE: Check containment.
        sitemap_prev = set(prev["sitemap"])
        sitemap = set(self.sitemap)

        return sitemap_prev - sitemap


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


cli = typer.Typer()
site = typer.Typer(callback=ContextSite.callback)

cli.add_typer(site, name="site")


# NOTE: Would like to pass either a directory or site.
@site.command("push")
def metadata_append(_context: typer.Context, *, force: FlagForce = False):
    "Pull source data into mongodb and keep."
    handler = SiteMetdataHandler(_context.obj)
    _id = handler.push(force=force)

    if _id is None:
        commit = handler.buildinfo.git_commit
        rich.print(f"[yellow]Data already exists for commit `{commit}`.")
        raise typer.Exit(203)

    data = handler.get(_id=_id)
    assert data is not None
    util.print_yaml(data["build_info"], name="build info")
    return


@site.command("test")
def metadata_test(_context: typer.Context):
    "Check source data against mongodb log."
    handler = SiteMetdataHandler(_context.obj)
    res = handler.test()
    if res is None:
        rich.print("[yellow]No entries to compare to.")
        raise typer.Exit(202)

    return


@site.command("show")
def metadata_show(_context: typer.Context):
    handler = SiteMetdataHandler(_context.obj)
    util.print_yaml(handler().model_dump(), name="metadata")


@cli.command("ping")
def ping(_mongodb_url: FlagMongodbURL = None):
    db.check_client(_mongodb_url)
