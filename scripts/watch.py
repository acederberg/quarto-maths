import contextlib
import http.server as http_server
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
from typing_extensions import Doc
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer

from scripts import env

path_here = pathlib.Path(__file__).parent.resolve()
path_build = path_here / "build"


class Context:
    quarto_verbose: bool
    quarto_filters: set[pathlib.Path]  # Use this to watch filter files.

    def __init__(
        self,
        quarto_verbose: bool = False,
        quarto_filters: Iterable[pathlib.Path] | None = None,
    ):
        self.quarto_verbose = quarto_verbose
        self.quarto_filters = (
            set(item.resolve() for item in quarto_filters)
            if quarto_filters is not None
            else set()
        )


class HandleWrite:
    context: Context

    tt_tolerance: Annotated[
        int,
        Doc("Acceptable time between writes. This is meant to make it easier."),
    ]
    tt_last: Annotated[
        dict[pathlib.Path, float],
        Doc("Map of file paths to last write timestamp."),
    ]
    path_memo: Annotated[
        dict[str, pathlib.Path],
        Doc("Map of seen paths to their resolved paths."),
    ]
    path_ignored: Annotated[
        set[str],
        Doc("Paths (from root) to ignore."),
    ]
    path_last_qmd: Annotated[
        pathlib.Path | None,
        Doc(
            "Last qmd file written to. This is used when watching filter "
            "files to determine which qmd files to re-render."
        ),
    ]

    def __init__(
        self,
        context: Context,
        *,
        tt_tolerance: int = 3,
        path_ignored: set[str] | None = None,
    ):

        self.tt_tolerance = tt_tolerance
        self.tt_last = dict()

        if path_ignored is None:
            self.path_ignored = {"build", ".quarto", "_freeze", "site_libs"}
        else:
            self.path_ignored = path_ignored

        self.path_memo = dict()
        self.path_last_qmd = None
        self.context = context

    def event_from_conform(self, path: pathlib.Path):
        """Check for sequential write events, e.g. from ``conform.nvim``
        fixing.
        """

        tt = time.time()
        tt_last = self.tt_last.get(path, 0)

        if abs(tt - tt_last) < self.tt_tolerance:
            return False

        self.tt_last[path] = tt
        return True

    def get_path(self, event: FileSystemEvent):
        _path_str = str(event.src_path)
        if event.src_path not in self.path_memo:
            self.path_memo[_path_str] = pathlib.Path(_path_str).resolve()

        return self.path_memo[_path_str]

    def is_ignored_path(self, path: pathlib.Path) -> bool:
        # NOTE: Do not ignore filters that are being watched.
        if path in self.context.quarto_filters:
            return False

        # NOTE: Ignore filters that are in any
        path_rel = os.path.relpath(path, path_here)
        top = path_rel.split("/")[0]

        return top in self.path_ignored

    def get_time_modified(self, path: pathlib.Path):
        return datetime.fromtimestamp(self.tt_last[path]).strftime("%H:%M:%S")

    def dispatch_qmd(self, path: pathlib.Path):
        error_output = env.BUILD / "error.txt"
        tt = self.get_time_modified(path)
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
            rich.print(
                f"[red]{tt} -> Failed to render `{path}`. See error output "
                "in `http://localhost:3000/error.txt`."
            )
        else:
            rich.print(f"[green]{tt} -> Rendered `{path}`.")
        if self.context.quarto_verbose:
            print(out.stdout)
            print(out.stderr.decode())

    def dispatch(self, event: FileSystemEvent) -> None:

        # NOTE: Parse and memoize path, decide if ignored.
        if event.event_type != "modified" or event.is_directory:
            return

        # NOTE: Resolve path from event and check if the event should be
        #       ignored.
        path = self.get_path(event)
        if self.is_ignored_path(path):
            return

        if self.event_from_conform(path):
            return

        # NOTE: If a qmd file was modified, then rerender the modified ``qmd``
        #       If a watched filter (from ``--quarto-filter``) is changed, do
        #       it for the last file.
        if path.suffix == ".qmd":
            self.dispatch_qmd(path)
            self.path_last_qmd = path
        elif path in self.context.quarto_filters and self.path_last_qmd is not None:

            tt = self.get_time_modified(path)
            rich.print(
                f"[blue]{tt} -> Changes detected in filter `{path}`, "
                f"tiggering rerender of `{self.path_last_qmd}`."
            )
            self.dispatch_qmd(self.path_last_qmd)

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
    event_handler = HandleWrite(context)
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)  # type: ignore
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
):
    context.obj = Context(
        quarto_verbose=quarto_verbose,
        quarto_filters=quarto_filters,
    )

    quarto_filters = [
        *(
            pth
            for pth in map(
                lambda item: env.SCRIPTS / "filters" / item,
                os.listdir(env.SCRIPTS / "filters"),
            )
            if pth.suffix == ".py"
        ),
        *quarto_filters,
    ]

    for path in quarto_filters:

        if os.path.exists(path):
            rich.print(f"[green]Watching filter `{path}`.")
        else:
            rich.print(
                f"[green]File `{path}` specified with `--quarto-verbose` does not exist."
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


if __name__ == "__main__":
    cli()
