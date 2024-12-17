from typing import Annotated

import bson
import fastapi
import motor.motor_asyncio

from acederbergio import db
from acederbergio.api import quarto, schemas


def db_config() -> db.Config:
    return db.Config()  # type: ignore


def db_db(config: "DbConfig") -> motor.motor_asyncio.AsyncIOMotorDatabase:
    return config.create_client_async()[config.database]


async def quarto_handler(db: "Db") -> quarto.Handler:

    current = await schemas.LogQuarto.latest(db)
    if not current:
        raise fastapi.HTTPException(500, detail={"msg": "No document."})

    print("depends", current.mongo_id)
    return quarto.Handler(
        context := quarto.Context(),
        quarto.Filter(context),
        mongo_id=bson.ObjectId(current.mongo_id),
    )


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


QuartoHandler = Annotated[quarto.Handler, fastapi.Depends(quarto_handler)]
DbConfig = Annotated[db.Config, fastapi.Depends(db_config, use_cache=True)]
Db = Annotated[
    motor.motor_asyncio.AsyncIOMotorDatabase,
    fastapi.Depends(db_db, use_cache=False),
]
