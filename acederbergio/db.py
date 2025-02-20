"""This module should contain the tools for establish connections with 
``mongodb`` and the associated commands.
"""

import json
from typing import Annotated, Any, Type

import bson
import pydantic
import rich
import typer
import yaml_settings_pydantic as ysp
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from acederbergio import env, util


def check_object_id(value) -> str | None:
    if isinstance(value, bson.ObjectId):
        return str(value)
    elif value is None:
        return value
    elif not bson.ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId.")
    return value


CONFIG = env.CONFIGS / "db.yaml"
DATABASE = "acederbergio"
URL = "mongodb://root:changeme@db:27017"

Aggr = list[dict[str, Any]]
FieldObjectId = Annotated[
    str | None,
    pydantic.Field(default=None, alias="_id"),
    pydantic.BeforeValidator(check_object_id),
]
FieldId = Annotated[
    str | None,
    pydantic.Field(default=None),
    pydantic.BeforeValidator(check_object_id),
]
FlagURL = Annotated[
    pydantic.MongoDsn, typer.Option("--mongodb-url"), pydantic.Field(URL)
]
FlagDatabase = Annotated[str, pydantic.Field(DATABASE)]


def create_client(
    *, _mongodb_url: pydantic.MongoDsn | str | None = None, cls: Type = MongoClient
):
    mongodb_url = env.require("mongodb_url", str(_mongodb_url))
    return cls(mongodb_url, server_api=ServerApi("1"))


class HasMongoId(pydantic.BaseModel):
    mongo_id: FieldObjectId


class Config(ysp.BaseYamlSettings):

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={CONFIG: ysp.YamlFileConfigDict(required=False)},
        env_prefix=env.name("mongodb_"),
    )

    database: FlagDatabase
    url: FlagURL
    include: Annotated[
        bool,
        pydantic.Field(
            default=env.ENV == "ci",
            description="""
            When mongodb is not required (e.g. during builds) use this to
            run without it. Some documents using this code do not need mongodb
            for one off renders. To set this, do

            .. code:: python

                ACEDERBERG_IO_MONGODB_INCLUDE=false

            and verify:

            .. code:: shell

                acederbergio db config 
        """,
        ),
    ]

    def create_client(self) -> MongoClient:
        return create_client(_mongodb_url=self.url)

    def create_client_async(self) -> AsyncIOMotorClient:
        return create_client(_mongodb_url=self.url, cls=AsyncIOMotorClient)

    # NOTE: While CLI flags can be use with ``cli_parse_args``, it does not look
    #       too good with ``typer``. It would be a great deal of work for something
    #       that is only somewhat useful.
    @classmethod
    def typerCallback(
        cls,
        context: typer.Context,
        # *,
        # url: FlagURL | None = None,
        # database: FlagDatabase | None = None,
    ):

        context.obj = cls()  # type: ignore


class BaseDBContext:
    """
    Minimal context for typer commands that use the database.
    """

    database: Config
    # config: T_Config

    _client: AsyncIOMotorClient | None
    _db: AsyncIOMotorDatabase | None

    def __init__(
        self,
        database: Config | None = None,
    ):
        self.database = database or Config.model_validate({})
        self._collection = None
        self._client = None

    @property
    def client(self) -> AsyncIOMotorClient:
        if self._client is None:
            self._client = self.database.create_client_async()

        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._collection is None:
            self._db = self.client[self.database.database]

        return self._db  # type: ignore


cli = typer.Typer(callback=Config.typerCallback, help="Mongodb connections.")


@cli.command("config")
def config(context: typer.Context):
    """View the current database configuration."""

    util.print_yaml(context.obj, name="MongoDB Config")  # type: ignore


@cli.command("ping")
def ping(context: typer.Context):
    """Verify database connectivity."""

    config: Config = context.obj
    client = config.create_client()
    rich.print("[green]Connecting...")
    try:
        res = client.admin.command("ping")
        rich.print("[green]Connection successful!")
        rich.print(f"[green]Response: {json.dumps(res)}")
    except Exception as err:
        rich.print("[red]Failed to connect.")
        rich.print("[red]" + str(err))
