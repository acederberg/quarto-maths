"""This script should generate ``icons.json`` (e.g. ``iconify``) from existing svgs 
so that icons are available for use with tools [mermaid](https://mermaid.js.org) 
that load the svg from json.
"""

import json
import os
import pathlib
from typing import Any, Iterable, Optional
from xml.dom import minidom

import rich.console
import typer

path_here = pathlib.Path(__file__).resolve().parent.parent
path_icons_json = path_here / "icons.json"
path_svg = path_here / "svg"
DELIM = "_"


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
        console.print(f"Could not find ``layer1`` of ``{path}``.")
        raise typer.Exit(1)

    return element.toxml("utf-8").decode()


def create_name(path: pathlib.Path):
    """Create name from ``path``."""
    head, _ = os.path.splitext(os.path.relpath(path, path_svg))
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
    return {create_name(item): create_iconify_icon(item) for item in walk(path_svg)}


def create_iconify_json(include: set[str] = set()):
    """Create ``kubernetes.json``, the iconify icon set."""

    icons = create_icons()
    if include:
        icons = {name: icon for name, icon in create_icons().items() if name in include}

    aliases = create_aliases(icons)
    return {"icons": icons, "prefix": "k8s", "aliases": aliases}


cli = typer.Typer()
console = rich.console.Console()

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


@cli.command("make")
def main(include: list[str] = list(), out: Optional[pathlib.Path] = None):

    iconify = create_iconify_json(set(include))

    if out is None:
        print(json.dumps(iconify, indent=2))
        return

    with open(out, "w") as file:
        json.dump(iconify, file, indent=2)


@cli.command("aliases")
def aliases(include: list[str] = list()):
    names = map(create_name, walk(path_svg))
    if include:
        _include = set(include)
        names = filter(lambda item: item in _include, names)

    aliases = create_aliases(names)
    print(json.dumps(aliases))


@cli.command("names")
def names():
    print(json.dumps(list(map(create_name, walk(path_svg)))))


if __name__ == "__main__":
    cli()
