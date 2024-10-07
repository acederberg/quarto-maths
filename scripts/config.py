import pathlib
from datetime import datetime
import logging
import sys
import yaml

from scripts import env

logger = logging.getLogger(__name__)

QUARTO = env.BLOG / "_quarto.yaml"
QUARTO_VARIABLES = env.BLOG / "_variables.yaml"


class Context:
    build_git_commit: str
    build_git_ref: str

    quarto_variables: pathlib.Path
    quarto: pathlib.Path
    google_tracking_id: str

    def __init__(
        self,
        *,
        build_git_commit: str,
        build_git_ref: str,
        google_tracking_id: str,
        quarto: pathlib.Path = QUARTO,
        quarto_variables: pathlib.Path = QUARTO_VARIABLES,
    ):

        self.build_git_commit = build_git_commit
        self.build_git_ref = build_git_ref

        self.quarto = quarto
        self.quarto_variables = quarto_variables
        self.google_tracking_id = google_tracking_id

    def set_tracking_id(self, dry: bool) -> int:
        logger.debug("Loading `%s`.", self.quarto)
        with open(self.quarto, "r") as file:
            data = yaml.safe_load(file)

        logger.debug("Updating `%s`.", self.quarto)
        if (website := data.get("website")) is None:
            print(f"`{QUARTO}` does not contain required key `website`.")
            return 1

        if website.get("google-analytics") is not None:
            print(f"`{QUARTO}` already has a value for `website.google-analytics`.")
            return 2

        website["google-analytics"] = self.google_tracking_id
        if dry:
            print("---")
            print("# _quarto.yaml\n")
            print(yaml.dump(website))
            return 0

        logger.debug("Dumping updated `%s`.", self.quarto)

        with open(self.quarto, "w") as file:
            yaml.safe_dump(data, file)

        return 0

    def spawn_variables(self, dry: bool) -> int:

        logger.debug("Adding variables to ``_variables.yaml``.")
        data = {
            "build_git_commit": self.build_git_commit,
            "build_git_ref": self.build_git_ref,
            "build_timestamp": datetime.timestamp(datetime.now()),
        }

        if dry:
            print("---")
            print("# _variables.yaml\n")
            print(yaml.dump(data))
            return 0

        with open(self.quarto_variables, "w") as file:
            yaml.dump(data, file)

        return 0


def main(
    _google_tracking_id: str | None = None,
    _dry: str = "1",
):



    dry = int(env.get("dry") or _dry) != 0
    context = Context(
        google_tracking_id=env.require("google_tracking_id", _google_tracking_id),
        build_git_commit=env.require("build_git_commit"),
        build_git_ref=env.require("build_git_ref"),
    )

    if out := context.set_tracking_id(dry):
        return out

    return context.spawn_variables(dry)


if __name__ == "__main__":
    code = main()
    sys.exit(code)
