"""This script should generate ``icons.json`` (e.g. ``iconify``) from existing svgs 
so that icons are available for use with tools [mermaid](https://mermaid.js.org) 
that load the svg from json.
"""

import json
import os
import pathlib
from typing import Any, Optional
from xml.dom import minidom

import rich.console
import typer

path_here = pathlib.Path(__file__).resolve().parent.parent
path_icons_json = path_here / "icons.json"
path_svg = path_here / "svg"


def walk(directory: pathlib.Path):
    contents = os.listdir(directory)

    for item in map(lambda item: directory / item, contents):

        if os.path.isdir(item):
            yield from walk(directory / item)
            continue

        yield directory / item


def load(path: pathlib.Path) -> str:
    # with open(path, "r") as file:
    #     return "".join(line.rstrip() for line in file.readlines())

    loaded = minidom.parse(str(path))
    elements = loaded.getElementsByTagName("g")
    element = next((ee for ee in elements if ee.getAttribute("id") == "layer1"), None)

    if element is None:
        console.print(f"Could not find ``layer1`` of ``{path}``.")
        raise typer.Exit(1)

    return element.toxml("utf-8").decode()


def create_name(item: pathlib.Path):
    head, _ = os.path.splitext(os.path.relpath(item, path_svg))
    pieces = head.split("/")

    # NOTE: Labeled icons are the default. When an icon is unlabeled, just
    #       attach ``unlabeled`` to the end.
    if "labeled" in pieces:
        pieces.remove("labeled")
    elif "unlabeled" in pieces:
        loc = pieces.index("unlabeled")
        pieces[loc], pieces[-1] = pieces[-1], "u"

    # NOTE: These prefixes are not necessary in icon names.
    if "infrastructure_components" in pieces:
        pieces.remove("infrastructure_components")
    elif "control_plane_components" in pieces:
        pieces.remove("control_plane_components")
    elif "resources" in pieces:
        pieces.remove("resources")

    return "-".join(pieces).replace("_", "-")


def create_content(path: pathlib.Path) -> dict[str, Any]:

    # NOTE: Height and width must be 17 to prevent cropping.
    return {"height": 17, "width": 17, "body": load(path)}


def create_icons():
    return {create_name(item): create_content(item) for item in walk(path_svg)}


def create_iconify_json(include: set[str] = set()):

    icons = create_icons()
    if include:
        icons = {name: icon for name, icon in create_icons().items() if name in include}

    return icons


cli = typer.Typer()
console = rich.console.Console()


@cli.command()
def main(include: list[str] = list(), out: Optional[pathlib.Path] = None):

    console.print(f"Dumping ``JSON`` to ``{out}``.")
    icons = create_iconify_json(set(include))
    iconify = {"icons": icons, "prefix": "k8s"}

    if out is None:
        print(json.dumps(iconify, indent=2))
        return

    with open(out, "w") as file:
        json.dump(iconify, file, indent=2)


if __name__ == "__main__":
    cli()
