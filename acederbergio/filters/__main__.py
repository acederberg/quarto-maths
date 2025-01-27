"""CLI Helpers for filters.

TODO

This module should define a 'metafilter' that combines all of the filters
available, so that the filter pipelines become shorter. For instance,
the document metadata:

```qmd
---
acederbergio:
  filters:
    - filter: floaty
      data: path/to/floaty.yaml
    - under_construction
  data: path/to/data/for/all.yaml
filters:
  - acederbergio
---
```

would use a combination of the document metadata and externalized metadata (in
addition to the metadata that quarto will add, too) in a single filter step to
invoke the ``floaty`` and ``under_construction`` filters.
This could save a substantial amount of time by dispatching pre-render checks
of filter configurations, since code cells will have to run and preliminary
pipeline steps must run first.
"""

import os
import pathlib
import subprocess
from typing import Annotated

import jsonpath_ng
import panflute as pf
import pydantic
import rich
import typer
import yaml
from rich import table

from acederbergio import env
from acederbergio import util as u
from acederbergio.filters import util

configs = typer.Typer()
cli = typer.Typer()
cli.add_typer(configs, name="configs")


@configs.command("list")
@configs.command("ls")
def show_configs_all():
    """Show all filter configurations available"""
    tt = table.Table()
    tt.add_column("Filter Name")
    tt.add_column("Filter Class")
    tt.add_column("Config Class")
    tt.add_column("Module")

    keys = ("name_filter", "name_filter_cls", "name_cls", "module")
    for item in util.config_infos().values():
        tt.add_row(
            *map(
                lambda key: str(item.get(key)),
                keys,
            )
        )

    rich.print(tt)


@configs.command("show")
def show_config(name: str):
    """Print out the ``JSON`` schema for a filter to see what it does."""

    config_infos = util.config_infos()
    if name not in config_infos:
        rich.print(f"[red]No such config `{name}`.")
        raise typer.Exit(1)

    config_info = config_infos[name]
    u.print_yaml(
        config_info["cls"].model_json_schema(),
        name=f"JSON Schema for `{name}`.",
    )


# TODO: Move this to API side, so that this data may be dispatched.
#       I would like to have a faster version that allow the loading usingg
#       artbitrary sources so that things move faster.
def get_metadata_fr(path):
    """Load document metadata using quarto.

    Slow. Use ``get_metadata_lazy`` instead.
    """

    temp = env.WORKDIR / "temp.json"
    os.remove(temp)

    # NOTE: Suppresses error where trys to move index. I want to report this bug,
    #       but have no time ATM.
    (_ := path.parent / "index.json").touch()

    # NOTE: Into file because pandoc does not like qmd extensions, also other
    #       obfuscating output leading to json parse errors. Further, ``pf``
    #       complains about the pandoc api version.
    cmd = ["quarto", "render", str(path), "--to", "json", "--out", str(temp)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode:
        rich.print(f"[red]Subprocess exited with status `{result.returncode}`.\n")
        rich.print(f"[red]Command: {' '.join(cmd)}")
        rich.print("[red]STDOUT\n\n" + result.stdout or "Nothing")
        rich.print("[red]STDERR\n\n" + result.stderr or "Nothing")

        # NOTE: Because when outputing to ``JSON``, it wants to move
        #       ``index.json`` which does not exist.
        if temp.exists():
            rich.print("[green]AST Dumped, continuing.")
        else:
            raise typer.Exit(1)

    with open(temp, "r") as file:
        doc = pf.load(file)

    return doc.get_metadata()  # type: ignore


def get_metadata_lazy(path: pathlib.Path):
    """Lazily load metadata from a source."""

    bounds = []
    with open(path) as file:
        if path.suffix in {".yaml", "yml"}:
            return yaml.safe_load(file)

        for line_no, line in enumerate(file.readlines()):
            if line.startswith("---"):
                bounds.append(line_no)

            if len(bounds) == 2:
                break

        start, stop = bounds
        file.seek(start)
        lines = [file.readline() for _ in range(stop - start)]

        return yaml.safe_load("".join(lines))


@configs.command("parse")
def parse_config(
    target: pathlib.Path,
    *,
    names: Annotated[list[str], typer.Option("--filter")] = list(),
    json_path: str | None = None,
    as_json: Annotated[bool, typer.Option("--json/--yaml")] = False,
    lazy: bool = True,
    validate: Annotated[bool, typer.Option("--validate/--raw")] = True,
    silent: Annotated[bool, typer.Option("--silent/--print")] = True,
):
    """Parse the configuration for a source."""

    # NOTE: Compoute model and json_filter before, because it is painful to
    #       wait for quarto just to have these fail.
    names = names or list(util.config_infos().keys())
    model = util.compile_model(*names) if validate else None
    path = target.resolve(strict=True)
    json_filter = jsonpath_ng.parse(json_path) if json_path is not None else None

    # NOTE: Get the data.
    data = get_metadata_fr(path) if not lazy else get_metadata_lazy(path)

    parsed = {key: data.get(key) for key in names}
    if model is not None:
        try:
            parsed = model.model_validate(parsed)
        except pydantic.ValidationError as err:
            # raise err
            rich.print("[red]Invalid configuration.")
            u.print_yaml(err.errors())
            raise typer.Exit(1) from err

        parsed = parsed.model_dump(mode="json", exclude_none=True)

    if json_filter is not None:
        parsed = list(item.value for item in json_filter.find(data))
        if len(parsed) == 1:
            parsed = parsed[0]

    if not silent:
        u.print_yaml(parsed, as_json=as_json)
    else:
        rich.print("[green]Configuration valid.")
