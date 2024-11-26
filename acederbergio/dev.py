"""Scripts for development.



This includes a custom watcher because I do not like the workflow I am forced
into be ``quarto preview``. A few problems I aim to solve here are:

1. Keeping static assets up to date.
2. Rendering the last rendered file when other non-qmd assets are written.
3. Putting debug messages.
"""

import contextlib
import http.server as http_server
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime
from typing import Annotated, Iterable

import pydantic
import rich
import rich.table
import typer
import yaml_settings_pydantic as ysp
from typing_extensions import Doc, Self
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from acederbergio import env, util

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


# class QuartoTargetType(enum.Enum, str):
#     filter = "filter"
#     asset = "asset"
#     static = "static"
#


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
                env.BLOG / "resume/template.tex",
                env.BLOG / "resume/title.tex",
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
    config: Config
    render: bool
    render_verbose: bool

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

    # ignore: Annotated[
    #     set[pathlib.Path],
    #     Doc("Absolute paths to ignore."),
    # ]

    def __init__(
        self,
        config: Config,
        *,
        quarto_verbose: bool = False,
        filters: Iterable[pathlib.Path] | None = None,
        render: bool = True,
        assets: Iterable[pathlib.Path] | None = None,
        static: Iterable[pathlib.Path] | None = None,
        ignore: Iterable[pathlib.Path] | None = None,
    ):
        self.config = config
        watch = self.config.watch

        self.render = render
        self.quarto_verbose = quarto_verbose or self.config.render.verbose
        self.filters = self.__validate_trie(filters or set(), watch.filters)
        self.assets = self.__validate_trie(assets or set(), watch.assets)
        self.static = self.__validate_trie(static or set(), watch.static)
        self.ignore = self.__validate_trie(ignore or set(), watch.ignore)

    def dict(self):
        out = {
            "ignore_trie": self.ignore.dict(),
            "filters": self.filters.dict(),
            "assets": self.assets.dict(),
            "static": self.static.dict(),
            "render": self.render,
            "quarto_verbose": self.quarto_verbose,
        }
        return out

    def __validate_trie(
        self,
        from_init: Iterable[pathlib.Path],
        from_config: Iterable[pathlib.Path],
    ) -> Node:
        return Node.fromPaths(*from_init, *from_config)

    def is_ignored_path(self, path: pathlib.Path) -> bool:
        # NOTE: Do not ignore filters that are being watched.
        if (
            self.filters.has_prefix(path)
            or self.assets.has_prefix(path)
            or self.static.has_prefix(path)
        ):
            return False

        # NOTE: See if the path lies in ignore directories.
        return self.ignore.has_prefix(path)

    # def __call__(self, path: pathlib.Path) -> QuartoTargetType | None:
    #
    #     if self.assets.has_prefix(path):
    #         return QuartoTargetType.asset
    #     elif self.filters.has_prefix(path):
    #         return QuartoTargetType.filter
    #     elif self.static.has_prefix(path):
    #         return QuartoTargetType.static
    #
    #     return None


class BlogHandler(FileSystemEventHandler):
    context: Context

    _ignored: Annotated[
        set[pathlib.Path],
        Doc("Cache for paths that make it past ``is_event_ignored``."),
    ]
    _path_memo: Annotated[
        dict[str, pathlib.Path],
        Doc("Cache map of seen paths to their resolved paths."),
    ]

    tt_tolerance: Annotated[
        int,
        Doc("Acceptable time between writes. This is meant to make it easier."),
    ]
    tt_last: Annotated[
        dict[pathlib.Path, float],
        Doc("Map of file paths to last write timestamp."),
    ]
    path_last_qmd: Annotated[
        pathlib.Path | None,
        Doc(
            "Last qmd file written to. This is used when watching filter "
            "files to determine which qmd files to re-render."
        ),
    ]
    suffixes = {
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

    def __init__(
        self,
        context: Context,
        *,
        tt_tolerance: int = 5,
    ):

        self.tt_tolerance = tt_tolerance
        self.tt_last = dict()

        self.path_last_qmd = None
        self.context = context

        self._ignored = set()
        self._path_memo = dict()

    def get_path(self, event: FileSystemEvent):
        _path_str = str(event.src_path)
        if event.src_path not in self._path_memo:
            self._path_memo[_path_str] = pathlib.Path(_path_str).resolve()

        return self._path_memo[_path_str]

    def get_time_modified(self, path: pathlib.Path):
        return datetime.fromtimestamp(self.tt_last[path]).strftime("%H:%M:%S")

    def render_qmd(
        self,
        path: pathlib.Path,
        *,
        tt: str | None = None,
        origin: pathlib.Path | None = None,
    ):
        """Render ``qmd``.

        If it fails, put the error content in the page."""

        error_output = env.BUILD / "error.json"
        if tt is None:
            tt = self.get_time_modified(path)

        if not self.context.render:
            logger.info("Not rendering `%s` because dry run.", path)
            return

        logger.info("Rendering quarto at `%s`", path)
        cmd = ["quarto", "render", str(path), *self.context.config.render.flags]

        rich.print(f"[green]{tt} -> Starting render for `{path}`. Command: `{cmd}`.")
        out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if out.returncode != 0:
            logger.info("Quarto render failed for path `%s`.", path)
            rich.print(f"[red]{tt} -> Failed to render `{path}`.")

            # NOTE: This content will be read in by error.qmd and then copied into
            #       place so that the error is displayed on refresh.
            with open(error_output, "w") as file:

                def clean(v):
                    ansi_escape = re.compile(r"\x1b\[.*?m")
                    return ansi_escape.sub("", v)

                json.dump(
                    {
                        "origin": str(origin or path),
                        "command": [" ".join(cmd)],
                        "timestamp": tt,
                        "stderr": clean(out.stdout.decode()).split("\n"),
                        "stdout": clean(out.stderr.decode()).split("\n"),
                    },
                    file,
                    indent=2,
                )

        else:
            logger.info("Quarto render succeeded for path `%s`.", path)
            rich.print(f"[green]{tt} -> Rendered `{path}`.")

        if self.context.quarto_verbose:
            print(out.stdout)
            print(out.stderr.decode())

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

    def is_event_ignored(
        self, v: FileSystemEvent | pathlib.Path
    ) -> pathlib.Path | None:
        # NOTE: Resolve path from event and check if the event should be
        #       ignored - next check if the event originates from conform.nvim.
        path = v if isinstance(v, pathlib.Path) else self.get_path(v)
        if path in self._ignored:
            logger.debug("Ignored `%s` since it has already been ignored.", path)
        elif self.context.is_ignored_path(path):
            logger.debug("Ignored event at `%s` because it is explicity ignored.", path)
        elif path.suffix not in self.suffixes:
            logger.debug("Ignored event at `%s` because of suffix.", path)
        elif self.is_event_from_conform(path):
            logger.debug(
                "Checking if event for path `%s` came from `conform.nvim`.", path
            )
        else:
            logger.debug("Not ignoring changes in `%s`.", path)
            return path

        return None

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        if (path := self.is_event_ignored(event)) is None:
            return

        # NOTE: If a qmd file was modified, then rerender the modified ``qmd``
        #       If a watched filter (from ``--quarto-filter``) is changed, do
        #       it for the last file.
        # NOTE: [About template partials](https://quarto.org/docs/authoring/includes.html).
        #       I will start all of my partials with an `_` and place them in a
        #       ``partials`` folder.
        is_partial = path.parent.name != "partials" and path.name.startswith("_")
        if path.suffix == ".qmd" and not is_partial:
            self.render_qmd(path)
            self.path_last_qmd = path
        elif (
            self.context.filters.has_prefix(path)
            or self.context.assets.has_prefix(path)
            or is_partial
        ):
            tt = self.get_time_modified(path)
            if self.path_last_qmd is None:
                logger.info("No render to dispatch from changes in `%s`.", path)
                rich.print(
                    f"[blue]{tt} -> Changes detected in `{path}`, no "
                    "``qmd`` to reload."
                )
                return

            logger.info(
                "Dispatching render of `%s` from changes in `%s`.",
                self.path_last_qmd,
                path,
            )
            rich.print(
                f"[blue]{tt} -> Changes detected in `{path}`, "
                f"tiggering rerender of `{self.path_last_qmd}`."
            )
            self.render_qmd(self.path_last_qmd, tt=tt, origin=path)
        elif self.context.static.has_prefix(path):
            path_dest = env.BUILD / os.path.relpath(path, env.BLOG)
            msg = "Copying `%s` to `%s`." % (path, path_dest)
            logger.info(msg)
            rich.print("[green]" + msg)
            shutil.copy(path, path_dest)
        else:
            self._ignored.add(path)

        # NOTE: Pain in the ass because of transient quarto html files.
        # elif path.suffix == ".html":
        #     dest = path_build / os.path.relpath(path, path_here)
        #     print(f"{path} -> {dest}")
        #     shutil.copy(path, dest)


class DualStackServer(http_server.ThreadingHTTPServer):

    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(
            request,
            client_address,
            self,
            directory=str(env.BUILD),  # type: ignore
        )


def watch(context: Context):
    event_handler = BlogHandler(context)
    observer = Observer()
    observer.schedule(event_handler, env.ROOT, recursive=True)  # type: ignore
    observer.start()
    try:
        while True:
            time.sleep(100)
    finally:
        observer.stop()
        observer.join()


def serve():
    http_server.test(  # type: ignore
        HandlerClass=http_server.SimpleHTTPRequestHandler,
        ServerClass=DualStackServer,
        port=3000,
        bind="0.0.0.0",
    )


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


def callback(
    context: typer.Context,
    quarto_verbose: FlagQuartoVerbose = False,
    render: FlagQuartoRender = True,
    filters: FlagFilters = list(),
    assets: FlagAsset = list(),
    ignore: FlagIgnore = list(),
):
    context.obj = Context(
        Config.model_validate({}),
        quarto_verbose=quarto_verbose,
        filters=filters,
        render=render,
        assets=assets,
        ignore=ignore,
    )


cli = typer.Typer(
    callback=callback,
    help="Blog development server and watcher.",
)
cli_context = typer.Typer(
    help="Watcher context debugging help.",
)
cli.add_typer(cli_context, name="context")


@cli.command("render")
def cmd_watch(_context: typer.Context):
    """Watch for changes and trigger rerenders."""
    context: Context = _context.obj

    watch(context)


@cli.command("server")
def cmd_server(_context: typer.Context):
    """Run the development server and watch for changes."""
    context: Context = _context.obj

    threading.Thread(target=serve).start()
    threading.Thread(target=lambda: watch(context)).start()


@cli_context.command("show")
def cmd_context_show(_context: typer.Context):
    """Show the current watcher context. Use for watcher debugging."""
    context: Context = _context.obj
    util.print_yaml(context.dict())


@cli_context.command("test")
def cmd_context_test(
    _context: typer.Context,
    paths: Annotated[list[pathlib.Path], typer.Argument()],
    max_depth: int = 3,
    max_rows: int = 50,
):
    """Given a directory, see what the watcher will ignore. Use for watcher debugging."""

    context: Context = _context.obj
    watcher = BlogHandler(context)

    t = rich.table.Table(title="Ignored Paths")
    t.add_column("Path")
    t.add_column("Ignored by ``is_ignored_path``")
    t.add_column("Ignored by ``is_ignored_event``")

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
                    str(context.is_ignored_path(p)),
                    str(watcher.is_event_ignored(p) is None),
                    str(depth),
                )
                rows += 1

        return rows

    add_paths(paths)
    rich.print(t)


if __name__ == "__main__":
    cli()
