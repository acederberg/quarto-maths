import pathlib
import logging
import sys
import yaml

from scripts import env

logger = logging.getLogger(__name__)

QUARTO = env.BLOG / "_quarto.yaml"


def main(quarto: pathlib.Path = QUARTO, _google_tracking_id: str | None = None, _dry: str = "1",):

    google_tracking_id = env.get("google_tracking_id", _google_tracking_id, required=True,)
    dry = int(env.get("dry") or _dry)

    logger.debug("Loading `%s`.", quarto)
    with open(quarto, "r") as file:
        data = yaml.safe_load(file)

    logger.debug("Updating `%s`.", quarto)
    if (website := data.get("website")) is None:
        print(f"`{QUARTO}` does not contain required key `website`.")
        return 1

    if website.get("google-analytics") is not None:
        print(f"`{QUARTO}` already has a value for `website.google-analytics`.")
        return 2

    website["google-analytics"] = google_tracking_id
    if dry:
        print(yaml.dump(website))
        return 0

    logger.debug("Dumping updated `%s`.", quarto)
    with open(quarto, "w") as file:
        yaml.safe_dump(data, file)

    return 0


if __name__ == "__main__":
    code = main()
    sys.exit(code)




