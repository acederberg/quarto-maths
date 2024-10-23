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
    tt_tolerance = 3
    tt_last: dict[pathlib.Path, float] = dict()
    memo: dict[str, pathlib.Path] = dict()
    ignored = {"build", ".quarto", "_freeze", "site_libs"}

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
            if event.src_path not in self.memo:
                self.memo[_path_str] = pathlib.Path(_path_str).resolve()

            path = self.memo[_path_str]

            path_rel = os.path.relpath(path, path_here)
            top = path_rel.split("/")[0]
            if top in self.ignored:
                return

            if path.suffix == ".qmd" and self.check_conform(path):
                out = subprocess.run(
                    ["quarto", "render", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                tt = datetime.fromtimestamp(self.tt_last[path]).strftime("%H:%M:%S")
                rich.print(f"[green]{tt} -> Rendered `{path}`.")
                if out.stderr and out.returncode != 0:
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


def watch():
    event_handler = HandleWrite()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(100)
    finally:
        observer.stop()
        observer.join()


def serve():
    http_server.test(
        HandlerClass=http_server.SimpleHTTPRequestHandler,
        ServerClass=DualStackServer,
        port=3000,
        bind="0.0.0.0",
    )


cli = typer.Typer()


@cli.command("watch")
def cmd_watch():
    watch()


@cli.command("server")
def cmd_server():
    threading.Thread(target=serve).start()
    threading.Thread(target=watch).start()


if __name__ == "__main__":
    cli()
