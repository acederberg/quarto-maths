import rich
import rich.syntax
import yaml


def print_yaml(data, *, name: str | None = None):
    s = rich.syntax.Syntax(
        "---\n" + (f"# {name}\n" if name is not None else "") + yaml.dump(data),
        "yaml",
        theme="fruity",
        background_color="default",
    )
    rich.print(s)
