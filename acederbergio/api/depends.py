from typing import Annotated

import fastapi
import motor.motor_asyncio
import uvicorn

from acederbergio import db
from acederbergio.api import schemas


def db_config() -> db.Config:
    return db.Config()  # type: ignore


def db_db(config: "DbConfig") -> motor.motor_asyncio.AsyncIOMotorDatabase:
    return config.create_client_async()[config.database]


# _og_handler = uvicorn.Server.handle_exit
#
#
# class AppState:
#     exiting: bool = False
#
#     @staticmethod
#     def handle_exit(*args, **kwargs):
#         AppState.should_exit = True
#         print(args, kwargs)
#         _og_handler(*args, **kwargs)
#
#
# uvicorn.Server.handle_exit = AppState.handle_exit


DbConfig = Annotated[db.Config, fastapi.Depends(db_config, use_cache=True)]
Db = Annotated[
    motor.motor_asyncio.AsyncIOMotorDatabase,
    fastapi.Depends(db_db, use_cache=False),
]
