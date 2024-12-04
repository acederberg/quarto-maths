import typer

from acederbergio.api.main import cli as cli_server
from acederbergio.config import cli as cli_config
from acederbergio.db import cli as cli_db
from acederbergio.env import cli as cli_env
from acederbergio.iconify import cli as cli_iconify_kubernetes
from acederbergio.verify import cli as cli_verify

cli = typer.Typer(pretty_exceptions_enable=False)
cli.add_typer(cli_server, name="serve")
cli.add_typer(cli_config, name="config")
cli.add_typer(cli_iconify_kubernetes, name="iconify")
cli.add_typer(cli_env, name="env")
cli.add_typer(cli_verify, name="verify")
cli.add_typer(cli_db, name="db")

if __name__ == "__main__":
    cli()
