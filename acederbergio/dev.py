"""Scripts for development.


This includes a custom watcher because I do not like the workflow I am forced
into be ``quarto preview``. A few problems I aim to solve here are:

1. Keeping static assets up to date.
2. Rendering the last rendered file when other non-qmd assets are written.
3. Putting debug messages.
"""

import asyncio
import contextlib
import json
import os
from typing import Any

import fastapi
import fastapi.staticfiles
import pydantic
import typer
import uvicorn
import uvicorn.config

from acederbergio import db, env
from acederbergio.api import quarto, routes, schemas

logger = env.create_logger(__name__)

# =========================================================================== #
# App Definition and Background Tasks.


def decode_jsonl(data_raw: bytes) -> list[dict[str, Any]] | None:
    """Parse JSON lines data into a list of datas.

    Data should be written to socket with newline endings.
    The socket should contain ``JSON`` lines formatted data.
    """

    try:
        data = [json.loads(item) for item in data_raw.split(b"\n") if item]
    except json.JSONDecodeError as err:
        print("`log_reciever` failed to decode invalid ``JSON`` content.")
        print(data_raw)
        print(err)
        return None

    return data


class Context:
    database: db.Config

    def __init__(self, database: db.Config | None = None):
        self.database = database or db.Config()  # type: ignore

    @classmethod
    def forTyper(cls, _context: typer.Context):
        if _context.obj is None:
            _context.obj = dict()

        _context.obj.update(database=db.Config())  # type: ignore


class DevApp:
    context: Context
    context_quarto: quarto.Context
    tasks: set[asyncio.Task]

    def __init__(self, context: Context, context_quarto: quarto.Context | None = None):
        self.context = context
        self.context_quarto = context_quarto or quarto.Context()

    # NOTE: This will allow records to be dynamically handled. Using a database
    #       handler directly would require a factory for logging, which is not a
    #       good fit with current patterns.
    async def watch_logs(self):
        """This should injest the logs from the logger using a unix socket."""

        # NOTE: Remove the unix domain socket before startup.
        async def handle_data(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ):
            logger.log(0, "Data recieved by logging socket.")
            data = await reader.read(4096)
            if (data_decoded := decode_jsonl(data)) is None:
                return

            writer.close()
            await asyncio.gather(
                writer.wait_closed(),
                schemas.Log.push(db, mongo_id, data_decoded),
            )

        socket_path = (env.ROOT / "blog.socket").resolve()
        if os.path.exists(socket_path):
            os.remove(socket_path)

        logger.debug("Initializing logging mongodb document.")
        client = self.context.database.create_client_async()
        db = client[self.context.database.database]

        res = await schemas.Log.spawn(db)
        mongo_id = res.inserted_id

        logger.info("Starting logging socket server.")
        server = await asyncio.start_unix_server(handle_data, path=str(socket_path))
        async with server:
            logger.info("Server listening at `%s`...", socket_path)
            await server.serve_forever()

    def handle(self, task: asyncio.Task):
        try:
            task.result()
        except Exception as err:
            raise ValueError("Task Failure.") from err

    @contextlib.asynccontextmanager
    async def lifespan(self, _: fastapi.FastAPI):

        self.tasks = {
            asyncio.create_task(self.watch_logs()),
            asyncio.create_task(quarto.watch()),
        }

        for task in self.tasks:
            task.add_done_callback(self.handle)

        yield

        for task in self.tasks:
            task.cancel()

    def create_app(self) -> fastapi.FastAPI:

        # NOTE: It would appear all other routes must be attched prior to this mount.
        app = fastapi.FastAPI(lifespan=self.lifespan)

        api_router = fastapi.APIRouter()
        routes.AppRoute.__class__.create_router(routes.AppRoute, api_router)

        app.include_router(api_router, prefix=routes.AppRoute.router_args["prefix"])
        app.mount("", fastapi.staticfiles.StaticFiles(directory=env.BUILD))

        return app


# NOTE: Must be invokable with no arguments for reload mode.
def create_app(context: Context | None = None):

    context = context or Context()  # type: ignore
    app = DevApp(context)
    return app.create_app()


def serve(context: Context, **kwargs):
    """

    This tends to produce an error in the logs when
    `WATCHFILES_IGNORE_PERMISSION_DENIED=0` is not set.
    """

    # kwargs["reload_dirs"] = [env.SCRIPTS]
    # kwargs["reload_excludes"] = [env.ROOT / "docker"]
    if not kwargs.get("host"):
        kwargs["host"] = "0.0.0.0"
    if not kwargs.get("port"):
        kwargs["port"] = 3000

    if kwargs.get("reload"):
        kwargs["factory"] = True
        logger.warning("Ignoring context from command line.")
        uvicorn.run(f"{__name__}:create_app", **kwargs)
    else:
        kwargs["factory"] = False
        app = create_app(context=context)
        uvicorn.run(app, **kwargs)


# =========================================================================== #


cli = typer.Typer(
    callback=Context.forTyper, help="Blog development server and watcher."
)
cli.add_typer(quarto.cli, name="context")


# @cli.command("render")
# def cmd_watch(_context: typer.Context):
#     """Watch for changes and trigger rerenders."""
#     context: Context = _context.obj
#
#     watch(context)
#
#
# @cli.command("fastapi")
# def cmd_fastapi():
#
#     config = db.Config()  # type: ignore
#     serve(config, reload=True)


@cli.command("server")
def cmd_server(_context: typer.Context):
    """Run the development server and watch for changes."""
    context: Context = _context.obj

    serve(context, reload=True)


# NOTE: Add rich formatting to uvicorn logs.
uvicorn.config.LOGGING_CONFIG.update(
    {
        "handlers": {
            "default": {
                "class": "rich.logging.RichHandler",
                "level": "DEBUG",
            },
        },
        "loggers": {"root": {"level": "INFO", "handlers": ["default"]}},
    }
)

if __name__ == "__main__":
    cli()
