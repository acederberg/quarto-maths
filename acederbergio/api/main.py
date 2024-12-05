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
import typer
import uvicorn
import uvicorn.config
import yaml

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


class App:
    context: Context
    context_quarto: quarto.Context
    tasks: dict[str, asyncio.Task]

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
            data = await reader.read(2**16)
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
            res = task.result()
            return res
        except asyncio.CancelledError:
            return
        except Exception as err:
            raise ValueError("Task Failure.") from err

    @contextlib.asynccontextmanager
    async def lifespan_dev(self, _: fastapi.FastAPI):
        """Development server lifespan.

        This should start a listener for the logging ``SocketHandler`` and
        for quarto renders.
        """

        watch = quarto.Watch()
        self.tasks = {
            "logs": asyncio.create_task(self.watch_logs()),
            "quarto": asyncio.create_task(watch()),
        }

        for task in self.tasks.values():
            task.add_done_callback(self.handle)

        yield

        assert watch.handler is not None

        logger.info("Dumping quarto watcher state.")
        with open(quarto.PATH_BLOG_HANDLER_STATE, "w") as file:
            yaml.dump(watch.handler.state.model_dump(mode="json"), file)

        for task in self.tasks.values():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                logger.info("Successfully exitted lifespan task.")

    def create_app(self) -> fastapi.FastAPI:

        # NOTE: It would appear all other routes must be attched prior to this mount.
        app = fastapi.FastAPI(lifespan=self.lifespan_dev if env.ENV_IS_DEV else None)

        api_router = fastapi.APIRouter()
        routes.ApiRoutes.__class__.create_router(routes.ApiRoutes, api_router)  # type: ignore[attr-defined]

        app.include_router(api_router, prefix=routes.ApiRoutes.router_args["prefix"])
        app.mount("", fastapi.staticfiles.StaticFiles(directory=env.BUILD, html=True))

        return app


# NOTE: Must be invokable with no arguments for reload mode.
def create_app(context: Context | None = None):

    context = context or Context()  # type: ignore
    app = App(context)
    return app.create_app()


def serve(context: Context, **kwargs):
    """Serve the application.

    The server will include a certain lifespan and particular routes depending
    on ``env.ENV``. For instance, quarto reloading is only available in
    development mode.
    """

    kwargs["reload_dirs"] = [str(env.SCRIPTS / "api")]
    kwargs["reload_excludes"] = [env.BLOG, env.ROOT / "docker", env.SCRIPTS / "filters"]

    if not kwargs.get("host"):
        kwargs["host"] = "0.0.0.0"
    if not kwargs.get("port"):
        kwargs["port"] = 3000

    if env.ENV_IS_DEV:
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


@cli.command("dev")
def cmd_server(_context: typer.Context):
    """Run the development server and watch for changes."""
    context: Context = _context.obj

    serve(context, reload=True)


# NOTE: Add rich formatting to uvicorn logs.
uvicorn.config.LOGGING_CONFIG.update(env.create_uvicorn_logging_config())

if __name__ == "__main__":
    cli()
