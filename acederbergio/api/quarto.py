"""
Quarto development utility.

This is used by the ``fastapi`` app to watch for changes in quarto website
assets and dispatch renders using the ``quarto render`` command.
It also adds metadata to the dispatched renders for the `live` filter.

:seealso: `LiveFilter`

It is also used to dispatch renders in docker builds so that a detailed report
of failed and successful renders can be had.
This module includes that ``acederbergio quarto`` command utility used directly
in ``docker`` builds.
"""

import asyncio
import os
import pathlib
import subprocess
import time
from typing import (Annotated, Any, AsyncGenerator, Awaitable, Callable,
                    ClassVar, Iterable, Iterator, Optional)

import bson
import motor
import motor.motor_asyncio
import pydantic
import rich
import rich.table
import typer
import watchfiles
import yaml
import yaml_settings_pydantic as ysp
from typing_extensions import Doc, Self

from acederbergio import db, env, util
from acederbergio.api import schemas

logger = env.create_logger(__name__)


# NOTE: This is possible with globs, but I like practicing DSA.
class Node:
    children: dict[str, Self]
    is_end: bool

    @classmethod
    def fromPaths(cls, *paths: pathlib.Path):
        root = Node(False)
        for path in paths:
            root.add(path)

        return root

    def __init__(self, is_end: bool):
        self.children = dict()
        self.is_end = is_end

    def add(self, path: pathlib.Path | str):

        if isinstance(path, str):
            path = pathlib.Path(path)

        path = path.resolve()

        node = self
        for item in path.parts:
            if item == "/":
                continue

            if item not in node.children:
                node.children[item] = self.__class__(False)

            node = node.children[item]

        node.is_end = True
        path.resolve()

    def has_prefix(self, path: pathlib.Path | str) -> bool:
        # NOTE: If the path encounters an end, it is ignored.

        if isinstance(path, str):
            path = pathlib.Path(path)

        path = path.resolve()

        node = self
        for item in path.parts:
            if item == "/":
                continue

            # NOTE: If the current node is terminating, definitely ignored.
            if node.is_end:
                return True

            # NOTE: No terminating node encountered, not ignored.
            if item not in node.children:
                return False

            node = node.children[item]

        return node.is_end

    def dict(self):

        out = dict()
        if self.is_end:
            out["is_end"] = self.is_end

        if self.children:
            out.update({k: v.dict() for k, v in self.children.items()})

        return out


class ConfigHandler(pydantic.BaseModel):
    verbose: Annotated[bool, pydantic.Field(default=False)]
    render: Annotated[bool, pydantic.Field(default=True)]
    flags: Annotated[
        list[str],
        pydantic.Field(
            default_factory=list,
            description="Additional flags for ``quarto render``.",
        ),
    ]


def create_set_defaults_validator(defaults: set[pathlib.Path]):
    def wrapper(v):
        if not isinstance(v, Iterable):
            return v

        v = set(v) | defaults
        return v

    return pydantic.BeforeValidator(wrapper)


class ConfigFilter(pydantic.BaseModel):
    """Configuration settings for ``Filter``."""

    filters: Annotated[
        set[pathlib.Path],
        pydantic.Field(default_factory=set, validate_default=True),
        create_set_defaults_validator(
            {
                env.SCRIPTS / "filters",
                env.BLOG / "filters",
            }
        ),
    ]
    assets: Annotated[
        set[pathlib.Path],
        pydantic.Field(default_factory=set, validate_default=True),
        create_set_defaults_validator(
            {
                env.BLOG / "includes",
                env.BLOG / "templates",
                env.BLOG / "themes",
                env.BLOG / "_quarto.yaml",
                env.BLOG / "resume/templates",
                env.BLOG / "resume/resume.yaml",
            }
        ),
    ]
    static: Annotated[
        set[pathlib.Path],
        pydantic.Field(default_factory=set, validate_default=True),
        create_set_defaults_validator(
            {
                env.BLOG / "js",
                env.BLOG / "icons/misc.json",
                env.BLOG / "icons/favicon.svg",
            }
        ),
    ]
    ignore: Annotated[
        set[pathlib.Path],
        pydantic.Field(default_factory=set, validate_default=True),
        create_set_defaults_validator(
            {
                env.BLOG / "build",
                env.BLOG / ".quarto",
                env.BLOG / "_freeze",
                env.BLOG / "site_libs",
                env.WORKDIR / ".git",
                env.WORKDIR / ".venv",
                env.WORKDIR / "docker",
                env.BLOG / "resume/test.tex",
                env.BLOG / "resume/index.tex",
                env.SCRIPTS / "api",
            }
        ),
    ]


class Config(ysp.BaseYamlSettings):
    """File configuration for :class:`Filter`, :class:`Handler`, and :class:`Watch`.

    Used by wrapping in :class:`Context` to include configuration for the database
    connection, verbosity, and renders..
    """

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={env.CONFIGS / "dev.yaml": ysp.YamlFileConfigDict(required=False)}
    )

    handler: Annotated[
        ConfigHandler,
        pydantic.Field(
            default_factory=dict,
            description="Settings for rendering.",
        ),
    ]
    filter: Annotated[
        ConfigFilter,
        pydantic.Field(
            description="Settings for the watcher.",
            default_factory=dict,
        ),
    ]


class Context:
    """
    Configuration for :class:`Filter`, :class:`Handler`, and :class:`Watch`.
    """

    database: db.Config
    config: Config

    _client: motor.motor_asyncio.AsyncIOMotorClient | None
    _db: motor.motor_asyncio.AsyncIOMotorDatabase | None

    def __init__(
        self,
        config: Config | None = None,
        database: db.Config | None = None,
        # *,
        # render_verbose: bool = False,
        # render: bool = True,
    ):
        self.database = database or db.Config()  # type: ignore
        self.config = config or Config()  # type: ignore

        # self.render = render
        # self.render_verbose = render_verbose or self.config.render.verbose

        self._collection = None
        self._client = None

    @classmethod
    def forTyper(
        cls,
        _context: typer.Context,
        render_verbose: "FlagHandlerVerbose" = False,
        render: "FlagHandlerRender" = True,
        # filters: "FlagFilterFilters" = list(),
        assets: "FlagFilterAsset" = list(),
        ignore: "FlagFilterIgnore" = list(),
    ):
        config_raw = {
            "handler": {"verbose": render_verbose, "render": render},
            "filter": {"assets": assets, "ignore": ignore},
        }
        context = Context(Config.model_validate(config_raw))
        filter = Filter(context)

        if _context.obj is None:
            _context.obj = dict()

        _context.obj.update(quarto_context=context, quarto_filter=filter)

    @property
    def client(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        if self._client is None:
            self._client = self.database.create_client_async()

        return self._client

    @property
    def db(self) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        if self._collection is None:
            self._db = self.client[self.database.database]

        return self._db  # type: ignore

    def dict(self):
        out = {
            "config": self.config.model_dump(mode="json"),
            "db": self.database.model_dump(mode="json"),
        }
        return out


# --------------------------------------------------------------------------- #
# Filter and Handlers


# NOTE: Should just support the right signature for ``__call__``.
#       Does not need to work like ``BaseFilter``.
#       See ``https://github.com/samuelcolvin/watchfiles/blob/main/watchfiles/filters.py``.
class Filter:
    """Determines which files are ignored and holds file categorization."""

    # fmt: off
    suffixes_deffered: ClassVar[set[str]] = { ".py", ".lua", ".qmd", ".html", ".yaml", ".css", ".scss", ".tex" }
    suffixes_static: ClassVar[set[str]] = { ".json", ".svg", ".js" }
    suffixes: ClassVar[set[str]] = suffixes_deffered | suffixes_static
    # fmt: on

    tt_tolerance: Annotated[
        int,
        Doc("Acceptable time between writes. This is meant to make it easier."),
    ]
    tt_last: Annotated[
        dict[pathlib.Path, float],
        Doc("Map of file paths to last write timestamp."),
    ]

    filters: Annotated[Node, Doc("Trie for matching watched filters.")]
    assets: Annotated[
        Node,
        Doc(
            "Trie for matching watched assets.\nThis should not include assets "
            "that ought to be literally coppied an pasted into their "
            "respective places in ``build``, for instance "
            "``icons/misc.json``.These should be in ``static``."
        ),
    ]
    static: Annotated[
        Node,
        Doc(
            "Trie for watching static assets.\nThis should contain assets that "
            "ought to be literally copied and pasted into build directly just "
            "like quarto would."
        ),
    ]
    ignore: Annotated[
        Node,
        Doc("Trie for matching ignored paths."),
    ]
    config: ConfigFilter

    def __init__(
        self,
        context: Context,
        *,
        tt_tolerance: int = 5,
        filters: Iterable[pathlib.Path] | None = None,
        assets: Iterable[pathlib.Path] | None = None,
        static: Iterable[pathlib.Path] | None = None,
        ignore: Iterable[pathlib.Path] | None = None,
    ) -> None:

        config = context.config.filter
        self.config = config
        self.filters = self.__validate_trie(filters or set(), config.filters)
        self.assets = self.__validate_trie(assets or set(), config.assets)
        self.static = self.__validate_trie(static or set(), config.static)
        self.ignore = self.__validate_trie(ignore or set(), config.ignore)

        self.tt_tolerance = tt_tolerance
        self.tt_last = dict()

    # TODO: Methods are often called twice - once to determine if the event is
    #       ignored, and again when ``Handler`` needs to determine what to do
    #       with the changes.
    def __call__(self, _: watchfiles.Change, path: str) -> bool:
        """
        Determine if a change is to be noticed or not.

        :param _:
        :param path: Path to the event.
        :returns: ``True`` if the file should be included in changes, ``False``
            if it should be ignored.
        """
        return not self.is_ignored(pathlib.Path(path))[0]

    def __validate_trie(
        self,
        from_init: Iterable[pathlib.Path],
        from_config: Iterable[pathlib.Path],
    ) -> Node:
        return Node.fromPaths(*from_init, *from_config)

    def dict(self):
        return {
            "ignore": self.ignore.dict(),
            "filters": self.filters.dict(),
            "assets": self.assets.dict(),
            "static": self.static.dict(),
        }

    def is_ignored(self, path: pathlib.Path) -> tuple[bool, str | None]:
        if self.ignore.has_prefix(path):
            logger.debug("`%s` ignored explicity.", path)
            return True, "explicit"
        elif path.is_dir():
            return True, "directory"
        elif path.suffix not in self.suffixes:
            return True, f"suffix={path.suffix}"
        elif self.is_event_from_conform(path):
            return True, "too close"
        elif (
            self.filters.has_prefix(path)
            or self.assets.has_prefix(path)
            or self.static.has_prefix(path)
        ):
            logger.debug("Not ignored.")
            return False, None

        logger.debug("Not ignoring changes in `%s`.", path)
        return False, None

    def is_event_from_conform(self, path: pathlib.Path):
        """Check for sequential write events, e.g. from ``conform.nvim``
        fixing.
        """

        tt = time.time()
        tt_last = self.tt_last.get(path, 0)

        self.tt_last[path] = tt
        if abs(tt - tt_last) < self.tt_tolerance:
            logger.debug("Event for `%s` came from `conform.nvim`.", path)
            return True

        return False


class Handler:
    """Handles events from ``watchfiles.awatch``.

    :ivar _from: From where did the handler originate? This field is used for
        render metadata.
    :ivar filter: :class:`Filter` instance used to determine how events are to
        be processed.
    :ivar context: :class:`Context` instance to configure the handler. Provides
        settings like `extra_flags` for the render command, ``dry_runs``, and a
        database configuration.
    :ivar mongo_id: Document to push render metadatas to. When noting is
        provided, no database opporations are required.
    """

    _from: schemas.QuartoRenderFrom
    filter: Filter
    context: Context

    mongo_id: bson.ObjectId | None

    def __init__(
        self,
        context: Context,
        filter: Filter,
        *,
        mongo_id: bson.ObjectId | None,
        _from: schemas.QuartoRenderFrom,
    ):
        self.filter = filter
        self.context = context
        self.mongo_id = mongo_id
        self._from = _from

    @property
    def config(self) -> ConfigHandler:
        return self.context.config.handler

    async def __call__(
        self,
        v: str | pathlib.Path,
        *,
        exclude_defered: bool = False,
    ) -> schemas.QuartoHandlerRender | schemas.QuartoHandlerJob | None:
        """Entrypoint for dispatching file renders.

        For rendering of directories, see :meth:`do_directory`.

        :param v: Path to render target.
        :param exclude_defered: Do not preform any defered renders. This setting
            is important for directory renders.
        :throws ValueError: If :param:`path` is to a directory.
        :returns: A ``QuartoRender`` object with logs and render metadata.
        """

        path = pathlib.Path(v).resolve() if isinstance(v, str) else v
        dispatch_kind = self.determine_dispatch_kind(path)

        if dispatch_kind == "static":
            return await self.do_static(path)
        elif dispatch_kind == "direct":
            return await self.do_qmd(path)
        elif dispatch_kind == "defered" and not exclude_defered:
            return await self.do_defered(path)

        return None

    def determine_dispatch_kind(
        self, path: pathlib.Path
    ) -> schemas.QuartoRenderKind | None:

        if os.path.isdir(path):
            raise ValueError("Cannot handle directory.")

        # NOTE: If a qmd file was modified, then rerender the modified ``qmd``
        #       If a watched filter (from ``--quarto-filter``) is changed, do
        #       it for the last file.
        # NOTE: [About template partials](https://quarto.org/docs/authoring/includes.html).
        #       I will start all of my partials with an `_` and place them in a
        #       ``partials`` folder.
        is_partial = path.parent.name == "partials" and path.name.startswith("_")
        if path.suffix == ".qmd" and not is_partial:
            return "direct"
        elif (
            self.filter.filters.has_prefix(path)
            or self.filter.assets.has_prefix(path)
            or is_partial
        ) and path.suffix in self.filter.suffixes_deffered:
            return "defered"
        elif (
            self.filter.static.has_prefix(path)
            and path.suffix in self.filter.suffixes_static
        ):
            return "static"

        return None

    # TODO: Should echo stdout when rendering. This will be helpful in for
    #       larger projects. What I would like in the end is to have the quarto
    #       overlay display the progress in real time using a websocket (or
    #       possible ``HTTP`` streaming) instead of an ``HTTP`` ``POST``
    #       request. This should be possible using ``process.communicate``.
    #
    #       For websockets, it would also be useful to have an event pushed for
    #       when the render starts.
    async def render_qmd(
        self,
        path: pathlib.Path,
        *,
        origin: pathlib.Path | None = None,
    ) -> schemas.QuartoHandlerRender | schemas.QuartoHandlerJob:
        """Render ``qmd`` by spinning up a subprocess for ``quarto render``.

        When ``env.VERBOSE`` is set ``true`` (by setting the environment
        variable ``"ACEDERBERG_IO_VERBOSE`` to any value besides ``0``, this
        will pretty print the render metadata to the terminal.


        :param path: Target of ``quarto render``.
        :param origin: Source of the render - e.g. changing a ``scss`` file
            will result in rendering again the last file rendered.
        :returns: A ``QuartoRender`` object containing render output and
            metadata *(besides when :ivar:`context.dry_run` is ``True``,
            this will return ``None``)*.
        """

        # NOTE: Cannot specify nested data with ``quarto render``.
        logger.info("Starting render of `%s`.", path)
        command = [
            "quarto",
            "render",
            str(path),
            "--metadata",
            f"live_file_path={path.relative_to(env.WORKDIR)}",
            *(config := self.config).flags,
        ]
        if not self.config.render:
            data = schemas.QuartoRenderJob(
                origin=str(origin),  # type: ignore
                target=str(path),
                command=command,
                item_from=self._from,
                kind="direct" if path == origin else "defered",
            )
            return schemas.QuartoHandlerResult(data=data)
        else:
            process = await asyncio.create_subprocess_shell(
                " ".join(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await process.wait()

            if code := process.returncode:
                logger.warning("Failed to render `%s`. Exit code `%s`.", path, code)
            else:
                logger.info("Rendered `%s`.", path)

            logger.debug("Pushing quarto logs document.")
            data = await schemas.QuartoRender.fromProcess(
                path,
                origin or path,
                process,
                command=command,
                kind="direct" if path == origin else "defered",
                _from=self._from,
            )

            if env.VERBOSE or config.verbose:
                color = "red" if data.status_code else "blue"
                util.print_yaml(
                    data,
                    name="Render Result",
                    as_json=True,
                    rule_title=f"Render of `{data.target}` at `{data.time}` from changes in `{data.origin}`",
                    rule_kwargs=dict(
                        characters="=", align="center", style=f"bold {color}"
                    ),
                )

            if self.mongo_id:
                await schemas.QuartoHistory.push(
                    self.context.db,
                    self.mongo_id,
                    [data.model_dump(mode="json")],
                )

            return schemas.QuartoHandlerResult(data=data)

    async def do_qmd(
        self, path: pathlib.Path
    ) -> schemas.QuartoHandlerResult | schemas.QuartoHandlerJob:
        """Render a ``qmd`` document from changes in itself.

        :param path:
        :returns:
        """

        data = await self.render_qmd(path, origin=path)

        return data

    async def do_defered(
        self, path: pathlib.Path
    ) -> schemas.QuartoHandlerResult | schemas.QuartoHandlerJob | None:
        """Filters, assets, and partials will have defered changes.

        In other words, the last modified qmd should be rerendered.

        :seealso: :meth:`render_qmd`.

        :param path:
        :returns:
        """

        if self.mongo_id is None:
            raise ValueError("Mongo ID is required to do defered renders.")

        filters = schemas.QuartoHistoryFilters(kind=["direct"])  # type: ignore
        history: Any = await schemas.QuartoHistory.last_rendered(
            self.context.db, filters=filters
        )

        if history is None:
            logger.info("No render to dispatch from changes in `%s`.", path)
            return None

        last = history.items[0]
        logger.info(
            "Dispatching render of `%s` from changes in `%s`.", last.target, path
        )
        data = await self.render_qmd(pathlib.Path(last.target).resolve(), origin=path)
        return data

    async def do_static(self, path: pathlib.Path) -> schemas.QuartoHandlerResult | None:
        """Static assets should be coppied to their respective location in
        ``build``.

        This is what ``quarto render`` would do too. However, ``quarto watch``
        is insufficient in this regard.

        :param path:
        :returns:
        """

        path_dest = env.BUILD / os.path.relpath(path, env.BLOG)
        command = ["cp", str(path), str(path_dest)]

        if not self.config.render:
            data = schemas.QuartoRenderJob(  # type: ignore
                command=command,
                item_from=self._from,
                kind="static",
                origin=str(path),
                target=str(path),
            )
            return schemas.QuartoHandlerResult(data=data)
        else:
            logger.info("Copying `%s` to `%s`.", path, path_dest)
            process = await asyncio.create_subprocess_shell(
                " ".join(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await process.wait()
            data = await schemas.QuartoRender.fromProcess(
                path,
                path_dest,
                process,
                command=command,
                kind="static",
                _from=self._from,
            )

            if self.mongo_id is not None:
                await schemas.QuartoHistory.push(
                    self.context.db,
                    self.mongo_id,
                    [data.model_dump(mode="json")],
                )

            return schemas.QuartoHandlerResult(data=data)

    async def do_directory(
        self,
        directory: str | pathlib.Path,
        *,
        depth_max: int = 5,
    ) -> AsyncGenerator[schemas.QuartoHandlerAny, None]:
        """Render a directory using quarto.

        :param directory:
        :param depth_max:
        :returns: An async generator yielding render results for each target rendered.
        """
        directory = pathlib.Path(directory) if isinstance(directory, str) else directory
        directory = directory.resolve()
        if not os.path.isdir(directory):
            raise ValueError(f"No such directory `{directory}`.")

        for item in self.walk(directory, depth_max=depth_max):
            if (res := await self(item, exclude_defered=True)) is None:
                _ = schemas.QuartoRenderRequestItem(  # type: ignore
                    path=str(item.relative_to(env.WORKDIR)),
                    kind="file",
                )
                yield schemas.QuartoHandlerRequest(data=_)
                continue

            yield res

    def walk(
        self,
        path: pathlib.Path | str,
        *,
        depth: int = 0,
        # items: int = 0,
        depth_max: int = 5,
        # max_items: int = 100,
    ) -> Iterator[pathlib.Path]:

        if isinstance(path, str):
            path = pathlib.Path(path).resolve()

        if depth > depth_max:
            return

        path = path.resolve()
        if path.suffix.startswith("_"):
            return

        if os.path.isdir(path):
            for item in os.listdir(path):
                yield from self.walk(path / item, depth=depth, depth_max=depth_max + 1)
        elif os.path.isfile(path) and not self.filter.is_ignored(path)[0]:
            yield path

        return

    # TODO: It would make more sense for this to be under ``__call__``.
    async def render(
        self,
        render_data: schemas.QuartoRenderRequest,
        # *,
        # callback: (
        #     Callable[
        #         [schemas.QuartoRender, schemas.QuartoRenderRequestItem],
        #         Awaitable[None],
        #     ]
        #     | None
        # ) = None,
        # T: Type[schemas.T_QuartoRenderResponseItem] = schemas.QuartoRender,
    ) -> AsyncGenerator[schemas.QuartoHandlerAny, None]:
        """
        Process :param:`render_data` and execute the callback.

        While the callback is not a pattern I like in python, it would be a
        mess to do this using async generators.

        :param render_data: Render request data.
        :param callback: Optional callback.
        """

        def resolve(data: schemas.QuartoHandlerAny | None) -> schemas.QuartoHandlerAny:
            return data if data is not None else schemas.QuartoHandlerRequest(data=item)

        # TODO: Could be dryer.
        data: schemas.QuartoHandlerAny | None
        for item in render_data.items:
            if item.kind == "file":
                yield resolve(await self(item.path))
                # if data is None:
                #     yield
                #     ignored.append(item)
                #     continue
                #
                # items.append(data)
                # if callback:
                #     await callback(data, item)

                # if data.status_code and render_data.exit_on_failure:
                #     break
            else:
                # NOTE: When render request items are emitted, then an item
                #       falied to render.
                iter_directory = self.do_directory(
                    item.path,
                    depth_max=item.directory_depth_max,
                )
                async for data in iter_directory:
                    yield resolve(data)

                    # if isinstance(data, schemas.QuartoRenderRequestItem):
                    #     ignored.append(data)
                    #     continue
                    # items.append(data)
                    # if callback:
                    #     await callback(data, item)
                    #
                    # if data.status_code and render_data.exit_on_failure:
                    #     break

        # NOTE: Directory items
        # return schemas.QuartoRenderResponse[schemas.QuartoRender](
        #     uuid_uvicorn=env.RUN_UUID,
        #     items=items,
        #     ignored=ignored,
        # )


class Watch:
    """Watch for changes to quarto documents and their dependencies using
    :class:`Filter` - dispatch renders for these changes using
    :class:`Handler`.

    :ivar context: Shared configuration for :ivar:`handler` and ivar:`filter`.
    :ivar filter: Filter instance configured by :ivar:`context`.
    :ivar handler: Handler configured by :ivar:`context`.
    :ivar include_mongo: Enable or disable pushing render metadata to mongodb.
    """

    context: Context
    filter: Filter
    handler: Handler | None
    include_mongo: bool

    def __init__(self, context: Context | None = None, include_mongo: bool = True):
        self.context = context or Context()
        self.filter = Filter(self.context)
        self.handler = None
        self.include_mongo = include_mongo

    async def get_handler(self) -> Handler:
        if self.handler is None:
            mongo_id = None
            if self.include_mongo:
                mongo_id = (
                    await schemas.QuartoHistory.spawn(self.context.db)
                ).inserted_id

            self.handler = Handler(
                self.context, self.filter, mongo_id=mongo_id, _from="lifespan"
            )

        return self.handler

    async def __call__(self, stop_event: asyncio.Event):
        """Watch for changes to quarto files and thier helpers.

        :param stop_event: An `asyncio.Event` that tells ``watchfiles`` to
            terminate.
        """

        handler = await self.get_handler()

        # NOTE: Shutting this down requires writing to a qmd after reload.
        #       `stop_event` has made this less of a problem.
        async for changes in watchfiles.awatch(
            env.WORKDIR,
            watch_filter=self.filter,
            step=1000,
            stop_event=stop_event,
        ):
            for _, path_raw in changes:
                path = pathlib.Path(path_raw)
                if path.parts[-1] == "_quarto.yaml":
                    await handler.do_defered(path)
                else:
                    await handler(path_raw)


# =========================================================================== #


FlagHandlerRender = Annotated[
    bool,
    typer.Option(
        "--render/--dry-run",
        help="Render writes or only watch for writes. Sets `config.handler.render`.",
    ),
]
FlagHandlerFilters = Annotated[
    list[pathlib.Path],
    typer.Option("--filter", help="Additional filters to watch."),
]
FlagHandlerVerbose = Annotated[
    bool,
    typer.Option(
        "--verbose",
        help=(
            "Print quarto output to the terminal. Note that output is "
            "available in ``error.txt`` in the quarto build directory or by "
            "the development server. Adds to `config.handler.verbose`."
        ),
    ),
]
FlagFilterAsset = Annotated[
    list[pathlib.Path],
    typer.Option(
        "--asset",
        help=(
            "Additional assets to watch. Assets will trigger rerenders of "
            "the last document when written to. Adds to `config.filter.asset`."
        ),
    ),
]
FlagFilterIgnore = Annotated[
    list[pathlib.Path],
    typer.Option("--ignore", help="Additional files too ignore."),
]

FlagRenderIsDirectory = Annotated[
    bool,
    typer.Option(
        "--directory/--file",
        help="""
            What is the render target kind? When a directory a specified in
            the positional argument but ``--file`` is provided, then the target
            will be ``index.qmd`` in that directory.",
            """,
    ),
]
FlagRenderSuccessesInclude = Annotated[
    bool,
    typer.Option(
        "--successes-include/--successes-exclude",
        help=" Include or exclude successful renders from terminal and fileoutput.",
    ),
]
FlagRenderOutput = Annotated[
    Optional[pathlib.Path],
    typer.Option("--output", help="File to output render report into."),
]
FlagRenderMongoInclude = Annotated[
    bool,
    typer.Option(
        "--mongo-include/--mongo-exclude",
        help="""
            Push data to the database. When ``--mongo-exclude`` is used
            database configuration environment variables/configuration should
            not be required. This is used to not need a database connection or
            configuration in docker builds.
        """,
    ),
]
FlagRenderSilent = Annotated[bool, typer.Option("--silent/--not-silent")]
FlagRenderExitOnFailure = Annotated[
    bool,
    typer.Option(
        "--on-failure-exit/--on-failure-continue",
        help="When a render fails, should the failure cause this command to exit?",
    ),
]


cli_context = typer.Typer(help="Watcher context debugging help.")
cli = typer.Typer(help="Quarto commands.", callback=Context.forTyper)
cli.add_typer(cli_context, name="context")


@cli_context.command("show")
def cmd_context_show(_context: typer.Context):
    """Show the current watcher context. Use for watcher debugging."""
    context: Context = _context.obj["quarto_context"]
    util.print_yaml(context.dict())


@cli_context.command("test")
def cmd_context_test(
    _context: typer.Context,
    paths: Annotated[list[pathlib.Path], typer.Argument()],
    max_depth: int = 3,
    max_rows: int = 50,
):
    """Given a directory, see what the watcher will ignore. Use for watcher debugging."""

    filter = _context.obj["quarto_filter"]
    context = _context.obj["quarto_context"]
    if context is None:
        raise ValueError()

    handler = Handler(context, filter, mongo_id=None, _from="client")

    t = rich.table.Table(title="Ignored Paths (``filter.is_ignored``)")
    t.add_column("Path")
    t.add_column("Render Kind")
    t.add_column("Ignored")
    t.add_column("Reason")

    def add_paths(paths: Iterable[pathlib.Path], depth=0, rows=0) -> int:
        """
        Returns the numver of rows encountered so far so that the table
        is not of unreasonable size, e.g. listing something stupid.
        """

        if depth > max_depth:
            return rows

        for path in paths:
            if rows > max_rows:
                break

            path = path.resolve()
            if os.path.isdir(path):
                rows = add_paths(
                    map(
                        lambda item: (path / item).resolve(),
                        os.listdir(path),
                    ),
                    depth=depth + 1,
                    rows=rows,
                )
            else:
                p = path.resolve()
                ignored, ignored_reason = filter.is_ignored(p)
                t.add_row(
                    str(p),
                    handler.determine_dispatch_kind(p),
                    str(ignored),
                    str(ignored_reason),
                    str(depth),
                )
                rows += 1

        return rows

    add_paths(paths)
    rich.print(t)


@cli.command("render")
def cmd_render(
    _context: typer.Context,
    path: Annotated[
        str,
        typer.Argument(
            help="Directory or file to render. When rendering a directory, add ``--directory``."
        ),
    ],
    *,
    max_depth: int = 5,
    is_directory: FlagRenderIsDirectory = False,
    include_success: FlagRenderSuccessesInclude = False,
    include_mongo: FlagRenderMongoInclude = True,
    output: FlagRenderOutput = None,
    silent: FlagRenderSilent = True,
    exit_on_failure: FlagRenderExitOnFailure = False,
):
    """Render quarto content in the same way that the API would."""

    async def callback(
        item: schemas.QuartoHandlerResult,
    ):
        data = item.data
        if not data.status_code and not include_success:
            rich.print(f"[green]Successfully rendered `{data.target}`!")
            return

        if not silent:
            util.print_yaml(
                data,
                rule_title="Render Result",
                rule_kwargs=dict(characters="=", align="center", style="bold blue"),
            )

    async def do_render():
        handler = await watch.get_handler()
        dry_run = not handler.config.render

        TT = schemas.QuartoRender if not dry_run else schemas.QuartoRenderJob
        SS = schemas.QuartoRenderResponse[TT]  # type: ignore
        result = await SS.fromHandlerResults(
            handler.render(data),
            callback=callback if not dry_run else None,
        )

        if dry_run and not output:
            util.print_yaml(
                result,
                rule_title="Dry Run Results.",
                rule_kwargs=dict(characters="=", style="bold blue"),
            )
            return

        if output is not None:
            rich.print(f"[green]Writing responses to `{output}`.")
            dumped = result if include_success or dry_run else result.get_failed()
            with open(str(output), "w") as file:
                yaml.safe_dump(dumped.model_dump(mode="json"), file)
            if dry_run:
                return

        has_failed_renders = result.any_failed()
        if has_failed_renders and exit_on_failure:
            failed = result.get_failed()
            util.print_yaml(
                failed,
                rule_title="Failed Renders",
                rule_kwargs=dict(characters="=", style="bold red"),
            )
            rich.print("[bold red]Failed for some renders.")
            raise typer.Exit(2)

    try:
        data = schemas.QuartoRenderRequest(
            exit_on_failure=exit_on_failure,
            items=[
                schemas.QuartoRenderRequestItem(
                    path=path,
                    kind="directory" if is_directory else "file",
                    directory_depth_max=max_depth,
                )
            ],
        )
    except pydantic.ValidationError as err:
        util.print_error(err)
        rich.print("[red]Invalid configuration.")

        raise typer.Exit(1)

    if not silent:
        util.print_yaml(
            data,
            rule_title="Request Data",
            rule_kwargs=dict(characters="#", align="center", style="bold cyan"),
        )

    context: Context = _context.obj["quarto_context"]
    watch = Watch(context, include_mongo=include_mongo)

    asyncio.run(do_render())


if __name__ == "__main__":
    cli()
