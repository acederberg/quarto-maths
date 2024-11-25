"""This script should generate ``icons.json`` (e.g. ``iconify``) from existing svgs 
so that icons are available for use with tools [mermaid](https://mermaid.js.org) 
that load the svg from json.
"""

import base64
import json
import os
import pathlib
from typing import Any, Iterable, Optional
from xml.dom import minidom

import requests
import rich.console
import typer

from acederbergio import env, util

PATH_HERE = pathlib.Path(__file__).resolve().parent
PATH_ICONS_JSON = PATH_HERE / "icons.json"
PATH_SVG = PATH_HERE / "svg"
DELIM = "_"

abbr = {
    "pvc": "persistent_volume-claim",
    "svc": "service",
    "vol": "volume",
    "rb": "role-binding",
    "rs": "replica-set",
    "ing": "ingress",
    "secret": "secret",
    "pv": "persistent-volume",
    "cronjob": "cron-job",
    "sts": "stateful-set",
    "pod": "pod",
    "cm": "config-map",
    "deploy": "deployment",
    "sc": "storage-class",
    "hpa": "horizontal-pod-autoscaler",
    "crd": "custom-resource-definition",
    "quota": "resource-quota",
    "psp": "pod-security-policy",
    "sa": "service-account",
    "role": "role",
    "c-role": "cluster-role",
    "ns": "namespace",
    "node": "node",
    "job": "job",
    "ds": "daemon-set",
    "ep": "endpoint",
    "crb": "cluster-role-binding",
    "limits": "limit-range",
    "control-plane": "control-plane",
    "k-proxy": "kube-proxy",
    "sched": "scheduler",
    "api": "api-server",
    "c-m": "controller-manager",
    "c-c-m": "cloud-controller-manager",
    "kubelet": "kubelet",
    "group": "group",
    "user": "user",
    "netpol": "network-policy",
}


def walk(directory: pathlib.Path):
    """Iterate through ``directory`` content."""
    contents = os.listdir(directory)

    for path in map(lambda path: directory / path, contents):

        if os.path.isdir(path):
            yield from walk(directory / path)
            continue

        yield directory / path


def load(path: pathlib.Path) -> str:
    """Load and process the ``svg`` file at ``path``."""

    loaded = minidom.parse(str(path))
    elements = loaded.getElementsByTagName("g")
    element = next((ee for ee in elements if ee.getAttribute("id") == "layer1"), None)

    if element is None:
        rich.print(f"[red]Could not find ``layer1`` of ``{path}``.")
        raise typer.Exit(1)

    return element.toxml("utf-8").decode()


def create_name(path: pathlib.Path):
    """Create name from ``path``."""
    head, _ = os.path.splitext(os.path.relpath(path, PATH_SVG))
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

    return DELIM.join(pieces).replace("-", DELIM)


def create_alias(name: str) -> str | None:
    """For a short name, create its long alias."""

    split = name.split("-")
    for pos, item in enumerate(split):
        if item in abbr:
            split[pos] = abbr[item]
        elif item == "u":
            split[pos] = "unlabeled"

    alias = DELIM.join(split).replace("-", DELIM)
    if alias == name:
        return None

    return alias


def create_aliases(names: Iterable[str]):
    """Create aliases ``$.aliases``."""

    aliases = {
        alias: {"parent": name}
        for name in names
        if (alias := create_alias(name)) is not None
    }
    return aliases


def create_iconify_icon(path: pathlib.Path) -> dict[str, Any]:
    """Create ``$.icons`` values."""

    # NOTE: Height and width must be 17 to prevent cropping.
    return {"height": 17, "width": 17, "body": load(path)}


def create_icons():
    """Create ``$.icons``."""
    return {create_name(item): create_iconify_icon(item) for item in walk(PATH_SVG)}


def create_iconify_json(include: set[str] = set()):
    """Create ``kubernetes.json``, the iconify icon set."""

    icons = create_icons()
    if include:
        icons = {name: icon for name, icon in create_icons().items() if name in include}

    aliases = create_aliases(icons)
    return {"icons": icons, "prefix": "k8s", "aliases": aliases}


cli = typer.Typer(help="Tool for generating the kubernetes iconify icon set.")


@cli.command("pull")
def pull(gh_token: Optional[str] = None):
    """Download the svgs from github using the API."""

    url_icons = "https://api.github.com/repos/kubernetes/community/contents/icons"
    gh_token = env.require("gh_token", gh_token)
    headers = {"Authorization": f"Bearer {gh_token}"}

    def get(url: str):
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(
                f"Bad status code `{response.status_code}` from `{response.request.url}`."
            )
            if response.content:
                print(response.json())
            raise typer.Exit(5)

        return response.json()

    def walk_clone(directory_relpath: str):

        directory_path = PATH_HERE / directory_relpath
        directory_url = url_icons + "/" + directory_relpath

        if not os.path.exists(directory_path):
            rich.print(f"[green]Making directory `{directory_path}`.")
            os.mkdir(directory_path)

        rich.print(f"[green]Checking contents of `{directory_path}`.")
        data = get(directory_url)

        for item in data:

            # NOTE: If it is a directory, recurse and inspect content.
            item_relpath = directory_relpath + "/" + item["name"]
            item_url = directory_url + "/" + item["name"]
            if item["type"] == "dir":
                walk_clone(item_relpath)
                continue

            # NOTE: If it is not a directory, then just put it into the file
            #       with its respective name.
            # NOTE: Content is in base64 form. There is the option to use the
            #       download_url field, however it is probably faster to do
            #       this.
            item_path = directory_path / item["name"]
            rich.print(f"[green]Inspecting `{item_relpath}`.")
            if not os.path.exists(item_path) and item_path.suffix == ".svg":
                rich.print(f"[green]Dumping content to `{item_path}`.")

                item_data = get(item_url)
                with open(item_path, "w") as file:
                    file.write(base64.b64decode(item_data["content"]).decode())

    walk_clone("svg")


@cli.command("make")
def main(include: list[str] = list(), out: Optional[pathlib.Path] = None):
    """Create kubernetes iconify json."""

    iconify = create_iconify_json(set(include))

    if out is None:
        util.print_yaml(iconify, as_json=True)
        return

    with open(out, "w") as file:
        json.dump(iconify, file, indent=2)


@cli.command("aliases")
def aliases(include: list[str] = list()):
    """Generate aliases and print to console."""

    names: Any = map(create_name, walk(PATH_SVG))
    if include:
        _include = set(include)
        names = filter(lambda item: item in _include, names)

    aliases = create_aliases(names)
    util.print_yaml(aliases, as_json=True)


@cli.command("names")
def names():
    """Generate names and print to console."""

    util.print_yaml(list(map(create_name, walk(PATH_SVG))), as_json=True)


if __name__ == "__main__":
    cli()
