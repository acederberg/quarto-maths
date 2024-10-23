import typer

from scripts.config import cli as cli_config
from scripts.iconify_kubernetes import cli as cli_iconify_kubernetes
from scripts.watch import cli as cli_watch

cli = typer.Typer()
cli.add_typer(cli_watch, name="dev")
cli.add_typer(cli_config, name="config")
cli.add_typer(cli_iconify_kubernetes, name="iconify")

if __name__ == "__main__":
    cli()
