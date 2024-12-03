from typing import Annotated

import fastapi
import motor.motor_asyncio

from acederbergio import db


def db_config() -> db.Config:
    return db.Config()  # type: ignore


def db_db(config: "DbConfig") -> motor.motor_asyncio.AsyncIOMotorDatabase:
    return config.create_client_async()[config.database]


DbConfig = Annotated[db.Config, fastapi.Depends(db_config, use_cache=True)]
Db = Annotated[
    motor.motor_asyncio.AsyncIOMotorDatabase,
    fastapi.Depends(db_db, use_cache=False),
]
