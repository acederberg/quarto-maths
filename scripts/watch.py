import contextlib
import http.server as http_server
import logging
import os
import pathlib
import socket
import subprocess
import threading
import time
from datetime import datetime
from typing import Annotated, Iterable, Optional

import rich
import typer
import yaml
from rich.logging import RichHandler
from typing_extensions import Doc, Self
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from scripts import env

logging.basicConfig(
    level=logging.WARNING, handlers=[RichHandler()], format="%(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# NOTE: This is possible with globs, but I like practicing DSA.
class IgnoreNode:

    children: dict[str, Self]
    is_end: bool

    def __init__(self, is_end: bool):
        self.children = dict()
        self.is_end = is_end

    def add(self, path: pathlib.Path | str):

        if isinstance(path, str):
            path = pathlib.Path(path)

        node = self
        for item in path.parts:
            if item == "/":
                continue

            if item not in node.children:
                node.children[item] = self.__class__(False)

            node = node.children[item]

        node.is_end = True
        path.resolve()

    def is_ignored(self, path: pathlib.Path | str) -> bool:
        # NOTE: If the path encounters an end, it is ignored.

        if isinstance(path, str):
            path = pathlib.Path(path)

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


class Context:
    quarto_render: bool
    quarto_verbose: bool
    quarto_filters: set[pathlib.Path]  # Use this to watch filter files.
    ignore: Annotated[
        set[pathlib.Path],
        Doc("Absolute paths to ignore."),
    ]
    ignore_trie: Annotated[
        IgnoreNode,
        Doc("Trie for matching ignored paths."),
    ]

    def __init__(
        self,
        quarto_verbose: bool = False,
        quarto_filters: Iterable[pathlib.Path] | None = None,
        quarto_render: bool = True,
        ignore: Iterable[pathlib.Path] | None = None,
    ):
        self.quarto_render = quarto_render
        self.quarto_verbose = quarto_verbose
        self.quarto_filters = self.__validate_filters(quarto_filters or set())

        self.ignore_trie = IgnoreNode(False)
        self.ignore = self.__validate_ignore(ignore or set())

    def dict(self):
        out = {
            "ignore_trie": self.ignore_trie.dict(),
            "quarto_filters": list(map(str, self.quarto_filters)),
            "quarto_render": self.quarto_render,
            "quarto_verbose": self.quarto_verbose,
        }
        return out

    def __validate_ignore(self, ignore: Iterable[pathlib.Path]) -> set[pathlib.Path]:

        logger.debug("Validating `Context.ignore`.")
        _ignore = (
            set(map(lambda item: pathlib.Path(item).resolve(), ignore))
            | set(
                map(
                    lambda item: (env.BLOG / item).resolve(),
                    ("build", ".quarto", "_freeze", "site_libs"),
                )
            )
            | set(map(lambda item: (env.ROOT / item).resolve(), (".git", ".venv")))
        )

        logger.debug("Assembling `context.ignore_trie`.")
        for path in _ignore:
            self.ignore_trie.add(path)

        return _ignore

    def __validate_filters(
        self, quarto_filters: Iterable[pathlib.Path]
    ) -> set[pathlib.Path]:
        logger.debug("Validating `context.filters`.")
        _quarto_filters = {
            *(
                pth
                for directory in (env.SCRIPTS, env.BLOG)
                for pth in map(
                    lambda item: (directory / "filters" / item).resolve(),
                    os.listdir(directory / "filters"),
                )
                if pth.suffix in {".py", ".lua"}
            ),
            *quarto_filters,
        }

        return _quarto_filters

    def is_ignored_path(self, path: pathlib.Path) -> bool:
        # NOTE: Do not ignore filters that are being watched.
        if path in self.quarto_filters:
            return False

        # NOTE: See if the path lies in ignore directories.
        return self.ignore_trie.is_ignored(path)


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
    suffixes = {".py", ".lua", ".qmd", ".html", ".yaml"}

    def __init__(
        self,
        context: Context,
        *,
        tt_tolerance: int = 3,
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

    def render_qmd(self, path: pathlib.Path, *, tt: str | None = None):
        error_output = env.BUILD / "error.txt"
        if tt is None:
            tt = self.get_time_modified(path)

        if not self.context.quarto_render:
            logger.info("Not rendering `%s` because dry run.", path)
            return

        logger.info("Rendering quarto at `%s`", path)
        rich.print(f"[green]{tt} -> Starting render for `{path}`.")
        out = subprocess.run(
            ["quarto", "render", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with open(error_output, "w") as file:
            file.write(out.stdout.decode())
            file.write(out.stderr.decode())

        if out.returncode != 0:
            logger.info("Quarto render failed for path `%s`.", path)
            rich.print(
                f"[red]{tt} -> Failed to render `{path}`. See error output "
                "in `http://localhost:3000/error.txt`."
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

    def is_event_ignored(self, event: FileSystemEvent) -> pathlib.Path | None:
        # NOTE: Resolve path from event and check if the event should be
        #       ignored - next check if the event originates from conform.nvim.
        path = self.get_path(event)
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
        if path.suffix == ".qmd":
            self.render_qmd(path)
            self.path_last_qmd = path
        elif path in self.context.quarto_filters:
            tt = self.get_time_modified(path)
            if self.path_last_qmd is None:
                logger.info("No render to dispatch from changes in `%s`.", path)
                rich.print(
                    f"[blue]{tt} -> Changes detected in filter `{path}`, no "
                    "``qmd`` to reload."
                )
                return

            logger.info(
                "Dispatching render of `%s` from changes in `%s`.",
                self.path_last_qmd,
                path,
            )
            rich.print(
                f"[blue]{tt} -> Changes detected in filter `{path}`, "
                f"tiggering rerender of `{self.path_last_qmd}`."
            )
            self.render_qmd(self.path_last_qmd, tt=tt)
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


FlagQuartoRender = Annotated[
    bool,
    typer.Option("--quarto-render/--dry"),
]
FlagQuartoFilters = Annotated[
    list[pathlib.Path],
    typer.Option("--quarto-filter"),
]
FlagQuartoVerbose = Annotated[
    bool,
    typer.Option("--quarto-verbose"),
]


def callback(
    context: typer.Context,
    quarto_verbose: FlagQuartoVerbose = False,
    quarto_filters: FlagQuartoFilters = list(),
    quarto_render: FlagQuartoRender = True,
):
    context.obj = Context(
        quarto_verbose=quarto_verbose,
        quarto_filters=quarto_filters,
        quarto_render=quarto_render,
    )


cli = typer.Typer(callback=callback)


@cli.command("render")
def cmd_watch(_context: typer.Context):
    context: Context = _context.obj

    watch(context)


@cli.command("server")
def cmd_server(_context: typer.Context):
    context: Context = _context.obj

    threading.Thread(target=serve).start()
    threading.Thread(target=lambda: watch(context)).start()


@cli.command("context")
def cmd_context(_context: typer.Context):
    context: Context = _context.obj

    print("---")
    print(yaml.dump(context.dict()))


if __name__ == "__main__":
    cli()
