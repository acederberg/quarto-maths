import pathlib
import subprocess
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

memo: dict[str, pathlib.Path] = dict()


class HandleWrite:
    tt_tolerance = 3
    tt_last = dict()

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

            if event.src_path not in memo:
                memo[event.src_path] = pathlib.Path(event.src_path).resolve()

            path = memo[event.src_path]

            if path.suffix == ".qmd":
                out = subprocess.run(
                    ["quarto", "render", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if out.stdout:
                    print(out.stdout)

                if out.stderr:
                    print(out.stderr.decode())


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
