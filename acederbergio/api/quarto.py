"""Quarto development utility."""

import asyncio
import os
import pathlib
import shutil
import subprocess
import time
from typing import Annotated, ClassVar, Iterable

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
PATH_BLOG_HANDLER_STATE = env.CONFIGS / ".blog-handler-state"
if not os.path.exists(PATH_BLOG_HANDLER_STATE):
    with open(PATH_BLOG_HANDLER_STATE, "w") as file:
        yaml.dump({}, file)


# NOTE: This is possible with globs, but I like practicing DSA.
class Node:
    """Trie for deciding what to ignore."""

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


class ConfigRender(pydantic.BaseModel):
    verbose: Annotated[bool, pydantic.Field(default=False)]
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


class ConfigWatch(pydantic.BaseModel):
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
                env.ROOT / ".git",
                env.ROOT / ".venv",
                env.ROOT / "docker",
                env.BLOG / "resume/test.tex",
                env.BLOG / "resume/index.tex",
            }
        ),
    ]


class Config(ysp.BaseYamlSettings):
    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={env.CONFIGS / "dev.yaml": ysp.YamlFileConfigDict(required=False)}
    )

    render: Annotated[
        ConfigRender,
        pydantic.Field(
            default_factory=dict,
            description="Settings for rendering.",
        ),
    ]
    watch: Annotated[
        ConfigWatch,
        pydantic.Field(
            description="Settings for the watcher.",
            default_factory=dict,
        ),
    ]


class Context:
    database: db.Config
    config: Config
    render: bool
    render_verbose: bool

    _client: motor.motor_asyncio.AsyncIOMotorClient | None
    _db: motor.motor_asyncio.AsyncIOMotorDatabase | None

    def __init__(
        self,
        config: Config | None = None,
        database: db.Config | None = None,
        *,
        render_verbose: bool = False,
        render: bool = True,
    ):
        self.database = database or db.Config()  # type: ignore
        self.config = config or Config()  # type: ignore

        self.render = render
        self.render_verbose = render_verbose or self.config.render.verbose
        self._collection = None
        self._client = None

    @classmethod
    def forTyper(
        cls,
        _context: typer.Context,
        render_verbose: "FlagQuartoVerbose" = False,
        render: "FlagQuartoRender" = True,
        filters: "FlagFilters" = list(),
        assets: "FlagAsset" = list(),
        ignore: "FlagIgnore" = list(),
    ):
        context = Context(
            Config.model_validate({}),
            render_verbose=render_verbose,
            render=render,
        )
        filter = Filter(
            context,
            filters=filters,
            assets=assets,
            ignore=ignore,
        )

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
            "render": self.render,
            "render_verbose": self.render_verbose,
        }
        return out


class HandlerState(ysp.BaseYamlSettings):
    """State to be carried accross reloads."""

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={
            PATH_BLOG_HANDLER_STATE: ysp.YamlFileConfigDict(required=True),
        }
    )

    path_last_qmd: Annotated[
        pathlib.Path | None,
        pydantic.Field(
            None,
            description=(
                "Last qmd file written to. This is used when watching filter "
                "files to determine which qmd files to re-render."
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# Filter and Handlers


# NOTE: Should just support the right signature for ``__call__``.
#       Does not need to work like ``BaseFilter``.
#       See ``https://github.com/samuelcolvin/watchfiles/blob/main/watchfiles/filters.py``.
class Filter:
    """Determines which files are ignored and holds file categorization."""

    # format: off
    suffixes: ClassVar[set[str]] = {
        ".py",
        ".lua",
        ".qmd",
        ".html",
        ".yaml",
        ".html",
        ".json",
        ".svg",
        ".css",
        ".scss",
        ".js",
        ".tex",
    }
    # format: on

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

        watch = context.config.watch
        self.filters = self.__validate_trie(filters or set(), watch.filters)
        self.assets = self.__validate_trie(assets or set(), watch.assets)
        self.static = self.__validate_trie(static or set(), watch.static)
        self.ignore = self.__validate_trie(ignore or set(), watch.ignore)

        self._ignored = set()
        self.tt_tolerance = tt_tolerance
        self.tt_last = dict()

    def __call__(self, _: watchfiles.Change, path: str) -> bool:
        """
        Returns:
            ``True`` if the file should be included in changes, ``False`` if it
            should be ignored.
        """
        return self.is_ignored_path(pathlib.Path(path))

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

    def is_ignored_path(self, path: pathlib.Path) -> bool:
        if self.ignore.has_prefix(path):
            return True
        # NOTE: Do not ignore filters, assets, or static items that are being watched.
        elif (
            self.filters.has_prefix(path)
            or self.assets.has_prefix(path)
            or self.static.has_prefix(path)
        ):
            return False
        elif path.suffix not in self.suffixes:
            logger.debug("Ignored event at `%s` because of suffix.", path)
            return True
        elif self.is_event_from_conform(path):
            logger.debug("Event for path `%s` came from `conform.nvim`.", path)
            return True
        else:
            logger.debug("Not ignoring changes in `%s`.", path)
            return False

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
    """Handles events from ``watchfiles.awatch``."""

    state: Annotated[HandlerState, Doc("State accross reloads.")]
    filter: Annotated[Filter, Doc("")]
    context: Annotated[Context, Doc("")]

    mongo_id: bson.ObjectId

    def __init__(
        self,
        context: Context,
        filter: Filter,
        *,
        mongo_id: bson.ObjectId,
    ):
        self.filter = filter
        self.context = context
        self.state = HandlerState()  # type: ignore
        self.mongo_id = mongo_id

    async def __call__(self, v: str) -> None:
        """Entrypoint."""

        if os.path.isdir(path := pathlib.Path(v)):
            return

        # NOTE: If a qmd file was modified, then rerender the modified ``qmd``
        #       If a watched filter (from ``--quarto-filter``) is changed, do
        #       it for the last file.
        # NOTE: [About template partials](https://quarto.org/docs/authoring/includes.html).
        #       I will start all of my partials with an `_` and place them in a
        #       ``partials`` folder.
        is_partial = path.parent.name == "partials" and path.name.startswith("_")
        if path.suffix == ".qmd" and not is_partial:
            await self.do_qmd(path)
        elif (
            self.filter.filters.has_prefix(path)
            or self.filter.assets.has_prefix(path)
            or is_partial
        ):
            return await self.do_defered(path)
        elif self.filter.static.has_prefix(path):
            return await self.do_static(path)

    async def render_qmd(
        self,
        path: pathlib.Path,
        *,
        # tt: str | None = None,
        origin: pathlib.Path | None = None,
    ):
        """Render ``qmd``.

        If it fails, put the error content in the page."""

        if not self.context.render:
            logger.info("Not rendering `%s` because dry run.", path)
            return

        logger.info("Starting render of `%s`.", path)
        command = ["quarto", "render", str(path), *self.context.config.render.flags]
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
        data = await schemas.LogQuartoItem.fromProcess(
            path or origin, process, command=command
        )

        if self.context.render_verbose:
            util.print_yaml(data)

        await schemas.LogQuarto.push(
            self.context.db,
            self.mongo_id,
            [data.model_dump(mode="json")],
        )

    async def do_qmd(self, path: pathlib.Path) -> None:
        """Render a ``qmd`` document in non-defered fasion."""

        await self.render_qmd(path)
        self.state.path_last_qmd = path

    async def do_defered(self, path: pathlib.Path) -> None:
        """Filters, assets, and partials will have defered changes.

        In other words, the last modified qmd should be rerendered.
        """

        if self.state.path_last_qmd is None:
            logger.info("No render to dispatch from changes in `%s`.", path)
            return

        logger.info(
            "Dispatching render of `%s` from changes in `%s`.",
            self.state.path_last_qmd,
            path,
        )
        return await self.render_qmd(self.state.path_last_qmd, origin=path)

    async def do_static(self, path: pathlib.Path) -> None:
        """Static assets should be coppied to their respective location in
        ``build``.

        This is what ``quarto render`` would do too. However, ``quarto watch``
        is insufficient in this regard.
        """

        path_dest = env.BUILD / os.path.relpath(path, env.BLOG)
        logger.info("Copying `%s` to `%s`.", path, path_dest)
        shutil.copy(path, path_dest)


async def watch(context: Context | None = None):
    """Watch for changes to quarto files and thier helpers."""

    if context is None:
        context = Context()

    logger.debug("Spawning quarto logs document.")
    res = await schemas.LogQuarto.spawn(context.db)

    filter = Filter(context)
    handler = Handler(context, filter, mongo_id=res.inserted_id)

    async for changes in watchfiles.awatch(env.ROOT, watch_filter=filter, step=1000):
        for _, path_raw in changes:
            await handler(path_raw)


# =========================================================================== #


FlagQuartoRender = Annotated[
    bool,
    typer.Option(
        "--quarto-render/--dry", help="Render writes or only watch for writes."
    ),
]
FlagFilters = Annotated[
    list[pathlib.Path],
    typer.Option("--quarto-filter", help="Additional filters to watch."),
]
FlagQuartoVerbose = Annotated[
    bool,
    typer.Option(
        "--quarto-verbose",
        help=(
            "Print quarto output to the terminal. Note that output is "
            "available in ``error.txt`` in the quarto build directory or by "
            "the development server."
        ),
    ),
]
FlagAsset = Annotated[
    list[pathlib.Path],
    typer.Option(
        "--quarto-asset",
        help=(
            "Additional assets to watch. Assets will trigger rerenders of "
            "the last document when written to."
        ),
    ),
]
FlagIgnore = Annotated[
    list[pathlib.Path],
    typer.Option("--ignore", help="Additional files too ignore."),
]

cli = typer.Typer(
    help="Watcher context debugging help.",
    callback=Context.forTyper,
)


@cli.command("show")
def cmd_context_show(_context: typer.Context):
    """Show the current watcher context. Use for watcher debugging."""
    context: Context = _context.obj["quarto_context"]
    util.print_yaml(context.dict())


@cli.command("test")
def cmd_context_test(
    _context: typer.Context,
    paths: Annotated[list[pathlib.Path], typer.Argument()],
    max_depth: int = 3,
    max_rows: int = 50,
):
    """Given a directory, see what the watcher will ignore. Use for watcher debugging."""

    filter = _context.obj["quarto_filter"]

    t = rich.table.Table(title="Ignored Paths")
    t.add_column("Path")
    t.add_column("Ignored by ``filter.is_ignored_path``")

    def add_paths(paths: Iterable[pathlib.Path], depth=0, rows=0) -> int:
        """Returns the numver of rows encountered so far so that the table
        is of unreasonable size, e.g. listing something stupid."""

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
                t.add_row(
                    str(p := path.resolve()),
                    str(filter.is_ignored_path(p)),
                    str(depth),
                )
                rows += 1

        return rows

    add_paths(paths)
    rich.print(t)


if __name__ == "__main__":
    cli()
