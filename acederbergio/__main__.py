import typer

from acederbergio.config import cli as cli_config
from acederbergio.env import cli as cli_env
from acederbergio.iconify_kubernetes import cli as cli_iconify_kubernetes
from acederbergio.watch import cli as cli_watch

cli = typer.Typer()
cli.add_typer(cli_watch, name="dev")
cli.add_typer(cli_config, name="config")
cli.add_typer(cli_iconify_kubernetes, name="iconify")
cli.add_typer(cli_env, name="env")

if __name__ == "__main__":
    cli()
