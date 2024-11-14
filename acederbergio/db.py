import json
from typing import Annotated, Any

import bson
import pydantic
import rich
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from acederbergio import env


def check_object_id(value: str) -> str:
    if isinstance(value, bson.ObjectId):
        return str(value)
    if not bson.ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return value


Aggr = list[dict[str, Any]]
FieldObjectId = Annotated[
    str | None,
    pydantic.Field(default=None, alias="_id"),
    pydantic.BeforeValidator(check_object_id),
]


def create_client(*, _mongodb_url: str | None = None):
    mongodb_url = env.require("mongodb_url", _mongodb_url)
    return MongoClient(mongodb_url, server_api=ServerApi("1"))


def check_client(_mongodb_url: str | None = None):

    client = create_client(_mongodb_url=_mongodb_url)
    try:
        res = client.admin.command("ping")
        rich.print("[green]Connection successful!")
        rich.print(f"[green]{json.dumps(res)}")
    except Exception as err:
        rich.print("[red]Failed to connect.")
        rich.print("[red]" + str(err))
