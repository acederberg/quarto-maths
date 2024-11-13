import pathlib
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Annotated, Any, Literal

import pydantic
import pymongo
import requests
import rich
import typer

from acederbergio import db, env, util

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
    urlset: list[SiteMapURLSet]

    @classmethod
    def fromXML(cls, xml: str):
        tree = ET.fromstring(xml)
        items = tree.findall("ns:url", SITEMAP_NAMESPACE)
        urlset = [SiteMapURLSet._fromXML(url) for url in items]
        return cls(urlset=urlset)  # type: ignore


class SiteMetdataHandler:
    context: "ContextSite"
    _client: pymongo.MongoClient | None
    _listings: Any | None
    _sitemap: Any | None

    def __init__(self, context: "ContextSite"):
        self.context = context
        self._client = None
        self._listings = None
        self._sitemap = None

    @property
    def client(self):
        if self._client is None:
            self._client = db.create_client(_mongodb_url=str(self.context.mongodb_url))
        return self._client

    @property
    def collection(self):
        db = self.client["acederberio"]
        return db.sitemaps

    @property
    def listings(self): ...

    @property
    def sitemap(self) -> SiteMap:

        if self._sitemap is None:
            self._sitemap = SiteMap.fromXML(self.get_content("sitemap.xml"))

        return self._sitemap

    def get_content(self, name: str) -> str:
        if self.context.source_kind == "directory":
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

    def dict(self):
        return {
            # "listings": self.listings.model_dump(),
            "sitemap": self.sitemap.model_dump(),
        }

    def push(self):
        return self.collection.insert_one(
            {
                "timestamp": int(datetime.timestamp(datetime.now())),
                "source": {
                    "kind": self.context.source_kind,
                    "source": self.context.source_kind or self.context.source_directory,
                    # "build_info": self.build_info,
                },
                "sitemap": self.sitemap.model_dump(mode="json", exclude_none=True),
                # "listings": self.sitemap.model_dump(mode="json", exclude_none=True),
            }
        ).inserted_id

    def view(self):
        # return self.collection.
        ...

    def test(self): ...


FlagSourceSite = Annotated[str | None, typer.Option("--site")]
FlagSourceDirectory = Annotated[str | None, typer.Option("--directory", "-d")]
FlagMongodbURL = Annotated[str | None, typer.Option("--mongodb-url")]
# "mongodb://root:changeme@db:27017"


class ContextSite(pydantic.BaseModel):
    """Context for the ``site`` command."""

    source_kind: Literal["site", "directory"]
    source_site: pydantic.AnyHttpUrl | None
    source_directory: pathlib.Path | None
    mongodb_url: Annotated[
        pydantic.MongoDsn,
        pydantic.Field(),
    ]

    def require_site(self) -> pydantic.AnyHttpUrl:
        if (source_site := self.source_site) is None:
            raise ValueError("Need site.")

        return source_site

    def require_directory(self) -> pathlib.Path:
        if (source_dir := self.source_directory) is None:
            raise ValueError("Need directory.")

        return source_dir

    @pydantic.model_validator(mode="before")
    def check_one_source(cls, v):

        v["mongodb_url"] = v.get("mongodb_url") or env.get("mongodb_url")
        source_site = v.get("source_site")
        source_directory = v.get("source_directory")
        if source_site is None and source_directory is None:
            raise ValueError(
                "At least one of ``--directory`` or ``--source_site`` is required."
            )
        if source_site is not None and source_directory is not None:
            raise ValueError("Cannot specify both of ``--directory`` and ``--site``.")

        v["source_kind"] = "site" if source_site is not None else "directory"
        v["source"] = source_site or source_directory

        return v


def callback(
    context: typer.Context,
    _mongodb_url: FlagMongodbURL = None,
    source_site: FlagSourceSite = None,
    source_directory: FlagSourceDirectory = None,
):
    try:
        context.obj = ContextSite(
            mongodb_url=_mongodb_url,  # type: ignore
            source_site=source_site,
            source_directory=source_directory,
        )
    except pydantic.ValidationError as err:

        for line in err.errors():
            print(line)
            rich.print(f'[red]{ line["msg"] }: {str(set(line["loc"]))}')

        raise typer.Exit(201) from err


cli = typer.Typer()
site = typer.Typer(callback=callback)

cli.add_typer(site, name="site")


# NOTE: Would like to pass either a directory or site.
@site.command("push")
def metadata_append(_context: typer.Context):
    "Pull source data into mongodb and keep."
    handler = SiteMetdataHandler(_context.obj)
    print(handler.push())

    return


@site.command("test")
def metadata_test(_context: typer.Context):
    "Check source data against mongodb log."
    handler = SiteMetdataHandler(_context.obj)
    print(handler.sitemap)
    return


@site.command("show")
def metadata_show(_context: typer.Context):
    handler = SiteMetdataHandler(_context.obj)
    util.print_yaml(handler.sitemap.model_dump(exclude_none=True), name="sitemap")


@cli.command("ping")
def ping(_mongodb_url: FlagMongodbURL = None):
    db.check_client(_mongodb_url)
