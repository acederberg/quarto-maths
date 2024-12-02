from typing import Annotated

import fastapi
import motor.motor_asyncio

from acederbergio import db


def db_config() -> db.Config:
    return db.Config()  # type: ignore


def db_client(config: "DbConfig") -> motor.motor_asyncio.AsyncIOMotorDatabase:
    return config.create_client_async()[config.database]


DbConfig = Annotated[db.Config, fastapi.Depends(db_config, use_cache=True)]
DbClient = Annotated[
    motor.motor_asyncio.AsyncIOMotorClient,
    fastapi.Depends(db_client, use_cache=False),
]
