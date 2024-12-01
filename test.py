import asyncio
import contextlib

import fastapi
import uvicorn


def index():
    return "It works!"


async def listener():

    while True:
        await asyncio.sleep(5)
        print("Doing background task.")


@contextlib.asynccontextmanager
async def lifespan(_: fastapi.FastAPI):

    task = asyncio.create_task(listener())
    yield

    task.cancel("stop it!")


def create_app():
    app = fastapi.FastAPI(lifespan=lifespan)
    app.get("/")(index)

    return app


if __name__ == "__main__":
    uvicorn.run(
        "test:create_app",
        factory=True,
        host="0.0.0.0",
        port=3000,
        reload=True,
    )
