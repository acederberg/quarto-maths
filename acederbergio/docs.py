"""Tools for generating site documentation."""

import griffe
import quartodoc
import typer
from quartodoc.__main__ import chdir

from acederbergio import env, util

QUARTO_CONFIG = env.BLOG / "_quarto.yaml"

cli = typer.Typer()


@cli.command("python")
def cli_create_python_docs() -> None:
    """Build python docs using ``quartodoc``."""

    builder: quartodoc.Builder = quartodoc.Builder.from_quarto_config(
        str(QUARTO_CONFIG)
    )

    griffe.load(
        "acederbergio",
        extensions=griffe.load_extensions({"griffe_pydantic": {"schema": True}}),
    )
    with chdir(env.BLOG):
        builder.build()


@cli.command("javascript")
def cli_create_javascript_docs() -> None:
    """Build javascript documentation using ``typedoc``."""

    util.CONSOLE.print("[red]Not implemented yet.")
    raise typer.Exit(1)


if __name__ == "__main__":
    cli()
