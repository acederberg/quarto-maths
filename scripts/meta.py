import json
import logging
import os
import pathlib
import sys
from typing import Any

import meta_tags_parser as mtp
import meta_tags_parser.structs as structs
import yaml

from scripts import env

logger = logging.getLogger("scripts.meta")


EXPECT_TWITTER = {"description", "title", "image", "card"}
EXPECT_OPEN_GRAPH = {"description", "title", "image", "type", "url"}


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


def check_taggroup(
    build_dir: pathlib.Path, tags: list[structs.OneMetaTag], expect: set[str]
):
    parsed = {item.name: item.value for item in tags}
    parsed_needs: list[Any] = [
        item for item in expect if item not in parsed or not parsed[item]
    ]

    if (
        "image" in expect
        and "image" in parsed
        and not parsed["image"].startswith("https://")
    ):
        image_path = (build_dir / parsed["image"].replace("/", "", 1)).resolve()

        if not os.path.exists(image_path):
            parsed_needs.append({"image_not_valid": {"path": str(image_path)}})

    if "url" in expect and "url" in parsed:
        url_path = (build_dir / parsed["url"].replace("/", "", 1)).resolve()

        if not os.path.exists(url_path):
            parsed_needs.append({"url_not_valid": {"path": str(url_path)}})

    if len(parsed_needs):
        return parsed_needs

    return None


def check_item(build_dir: pathlib.Path, item_path: pathlib.Path):
    item_content = load_item(item_path)
    report = mtp.parse_meta_tags_from_source(item_content)

    out = dict()
    if (
        twitter_missing := check_taggroup(build_dir, report.twitter, EXPECT_TWITTER)
    ) is not None:
        out["twitter"] = twitter_missing

    if (
        og_missing := check_taggroup(build_dir, report.open_graph, EXPECT_OPEN_GRAPH)
    ) is not None:
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
                build_dir, item_path := (build_dir / item.replace("/", "", 1)).resolve()
            )
        )
        is not None
    ]


def main(_build_dir: pathlib.Path = env.BUILD) -> int:
    if (build_dir_env := env.get("build", required=False)) is not None:
        build_dir = pathlib.Path(build_dir_env).resolve()
    else:
        build_dir = _build_dir

    logger.info("Checking build in `%s`.", build_dir)

    report = [
        item
        for listing_item in load_listings(build_dir)
        if (report_item := check_listing(build_dir, listing_item))
        for item in report_item
    ]
    if report:
        print(yaml.safe_dump(report, indent=2))
        return 1

    return 0


if __name__ == "__main__":
    code = main()
    sys.exit(code)
