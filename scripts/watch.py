import contextlib
import http.server as http_server
import os
import pathlib
import socket
import subprocess
import threading
import time
from datetime import datetime

import rich
import typer
from watchdog.events import FileSystemEvent
from watchdog.observers import Observer

from scripts import env

path_here = pathlib.Path(__file__).parent.resolve()
path_build = path_here / "build"


class HandleWrite:
    quarto_verbose: bool
    tt_tolerance: int
    tt_last: dict[pathlib.Path, float]
    path_memo: dict[str, pathlib.Path]
    path_ignored: set[str]

    def __init__(
        self,
        quarto_verbose: bool = False,
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
        self.quarto_verbose = quarto_verbose

    def check_conform(self, path: pathlib.Path):
        """Check for sequential write events, e.g. from ``conform.nvim``
        fixing.
        """

        tt = time.time()
        tt_last = self.tt_last.get(path, 0)

        if abs(tt - tt_last) < self.tt_tolerance:
            return False

        self.tt_last[path] = tt
        return True

    def dispatch(self, event: FileSystemEvent) -> None:

        if event.event_type == "modified" and not event.is_directory:

            _path_str = str(event.src_path)
            if event.src_path not in self.path_memo:
                self.path_memo[_path_str] = pathlib.Path(_path_str).resolve()

            path = self.path_memo[_path_str]

            path_rel = os.path.relpath(path, path_here)
            top = path_rel.split("/")[0]
            if top in self.path_ignored:
                return

            if path.suffix == ".qmd" and self.check_conform(path):
                out = subprocess.run(
                    ["quarto", "render", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                tt = datetime.fromtimestamp(self.tt_last[path]).strftime("%H:%M:%S")
                rich.print(f"[green]{tt} -> Rendered `{path}`.")
                if (out.stderr and out.returncode != 0) or self.quarto_verbose:
                    print(out.stdout)
                    print(out.stderr.decode())

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


def watch(quarto_verbose: bool = False):
    event_handler = HandleWrite(quarto_verbose=quarto_verbose)
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


class Context:
    quarto_verbose: bool

    def __init__(self, quarto_verbose: bool = False):
        self.quarto_verbose = quarto_verbose


def callback(context: typer.Context, quarto_verbose: bool = False):
    context.obj = Context(quarto_verbose=quarto_verbose)


cli = typer.Typer(callback=callback)


@cli.command("render")
def cmd_watch(_context: typer.Context):
    context: Context = _context.obj

    watch(quarto_verbose=context.quarto_verbose)


@cli.command("server")
def cmd_server(_context: typer.Context):
    context: Context = _context.obj

    threading.Thread(target=serve).start()
    threading.Thread(target=lambda: watch(context.quarto_verbose)).start()


if __name__ == "__main__":
    cli()
