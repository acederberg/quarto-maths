"""This module should contain the tools for establish connections with 
``mongodb`` and the associated commands.
"""

import json
from typing import Annotated, Any

import bson
import pydantic
import rich
import typer
import yaml_settings_pydantic as ysp
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


CONFIG = env.CONFIGS / "mongodb.yaml"
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
FlagURL = Annotated[str, typer.Option("--mongodb-url"), pydantic.Field(URL)]
FlagDatabase = Annotated[str, pydantic.Field(DATABASE)]


def create_client(*, _mongodb_url: str | None = None):
    mongodb_url = env.require("mongodb_url", _mongodb_url)
    return MongoClient(mongodb_url, server_api=ServerApi("1"))


class Config(ysp.BaseYamlSettings):

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={CONFIG: ysp.YamlFileConfigDict(required=False)},
        env_prefix=env.name("mongodb_"),
    )

    database: FlagDatabase
    url: FlagURL

    def create_client(self):
        return create_client(_mongodb_url=self.url)

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
