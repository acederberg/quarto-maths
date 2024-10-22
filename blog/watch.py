import os
import pathlib
import shutil
import subprocess
import time

from watchdog.events import FileSystemEvent
from watchdog.observers import Observer

path_here = pathlib.Path(__file__).parent.resolve()
path_build = path_here / "build"


class HandleWrite:
    tt_tolerance = 3
    tt_last = dict()
    memo: dict[str, pathlib.Path] = dict()

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
            if "build" in event.src_path:
                return

            if event.src_path not in self.memo:
                self.memo[event.src_path] = pathlib.Path(event.src_path).resolve()

            path = self.memo[event.src_path]

            if path.suffix == ".qmd" and self.check_conform(path):
                out = subprocess.run(
                    ["quarto", "render", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                print(int(self.tt_last[path]), path)
                if out.stderr and out.returncode != 0:
                    print(out.stdout)
                    print(out.stderr.decode())

            # NOTE: Pain in the ass because of transient quarto html files.
            # elif path.suffix == ".html":
            #     dest = path_build / os.path.relpath(path, path_here)
            #     print(f"{path} -> {dest}")
            #     shutil.copy(path, dest)


def main():
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


if __name__ == "__main__":
    main()
