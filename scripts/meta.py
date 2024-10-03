import sys
from os import environ
import os
import pathlib
from typing import Any
import json
import logging
import meta_tags_parser as mtp
import meta_tags_parser.structs as structs
import yaml


logger = logging.getLogger("scripts.meta")


ENV_PREFIX = "ACEDERBERG_IO"
BUILD_DIR = pathlib.Path(__file__).resolve().parent.parent / "build"
EXPECT_TWITTER = {"description", "title", "image", "card"}
EXPECT_OPEN_GRAPH = {"description", "title", "image", "type", "url"}


def get(varname: str, *, default: str | None = None) -> str:
    logger.debug("Getting variable `%s`.", varname)
    out = environ.get(f"{ENV_PREFIX}_{varname.upper()}", default)
    if out is None:
        raise ValueError(f"Could not resolve for variable `{varname}`.")

    return out


def load_listings(build_dir: pathlib.Path) -> list[dict[str, Any]]:
    listings_path = build_dir / "listings.json"
    logger.info("Loading listings from `%s`.", listings_path)

    with open(listings_path, "r") as file:
        listings = json.load(file)

    return listings


def load_item(item: pathlib.Path):
    logger.debug("Loading `%s`.", item)
    with open(item, "r") as file:
        content = "\n".join(file.readlines())

    return content


def check_taggroup(build_dir: pathlib.Path, tags: list[structs.OneMetaTag], expect: set[str]):
    parsed = {item.name: item.value for item in tags}
    parsed_needs: list[Any] = [item for item in expect if item not in parsed or not parsed[item]]

    if "image" in expect and "image" in parsed and not parsed["image"].startswith("https://"):
        image_path = (build_dir / parsed["image"].replace("/", "", 1)).resolve()

        if not os.path.exists(image_path):
            parsed_needs.append({"image_not_valid": {"path": str(image_path)}})


    if len(parsed_needs):
        return parsed_needs

    return None


def check_item(build_dir: pathlib.Path, item_path: pathlib.Path):
    item_content = load_item(item_path)
    report = mtp.parse_meta_tags_from_source(item_content)

    out = dict()
    if (twitter_missing := check_taggroup(build_dir, report.twitter, EXPECT_TWITTER)) is not None:
        out["twitter"] = twitter_missing

    if (og_missing := check_taggroup(build_dir, report.open_graph, EXPECT_OPEN_GRAPH)) is not None:
        out["open_graph"] = og_missing

    if not len(out):
        return None

    return out


def check_listing(build_dir: pathlib.Path, listing_item: dict[str, Any]):
    logger.debug("Checking `%s`.", listing_item)

    if "listing" not in listing_item or "items" not in listing_item:
        raise ValueError(f"Invalid listing `{listing_item}`.")

    return [
        {**report, "path": str(item_path)}
        for item in listing_item["items"]
        if (
            report := check_item(
                build_dir,
                item_path := (build_dir / item.replace("/", "", 1)).resolve()
            )
        )
        is not None
    ]


def main(_build_dir: str = "build"):
    build_dir = pathlib.Path(get(ENV_PREFIX, default=_build_dir)).resolve()
    logger.info("Checking build in `%s`.", build_dir)

    report = [
        item
        for listing_item in load_listings(build_dir)
        if (report_item := check_listing(build_dir, listing_item))
        for item in report_item
    ]
    if report:

        print(yaml.safe_dump(report, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
