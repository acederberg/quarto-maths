import typer

from acederbergio.api.main import cli as cli_server
from acederbergio.api.quarto import cli as cli_quarto
from acederbergio.pdf import cli as cli_pdf
from acederbergio.config import cli as cli_config
from acederbergio.db import cli as cli_db
from acederbergio.docs import cli as cli_docs
from acederbergio.env import cli as cli_env
from acederbergio.filters.__main__ import cli as cli_filters
from acederbergio.iconify import cli as cli_iconify_kubernetes
from acederbergio.verify import cli as cli_verify

cli = typer.Typer(pretty_exceptions_enable=False)
cli.add_typer(cli_pdf, name="pdf")
cli.add_typer(cli_quarto, name="quarto")
cli.add_typer(cli_server, name="serve")
cli.add_typer(cli_docs, name="docs")
cli.add_typer(cli_config, name="config")
cli.add_typer(cli_iconify_kubernetes, name="iconify")
cli.add_typer(cli_env, name="env")
cli.add_typer(cli_verify, name="verify")
cli.add_typer(cli_db, name="db")
cli.add_typer(cli_filters, name="filters")

if __name__ == "__main__":
    cli()
