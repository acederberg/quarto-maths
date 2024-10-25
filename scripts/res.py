"""This should turn ``resume.yaml`` into a quarto document to so that I do not have
to suffer writing long paths, conditional content, and copy/paste in quarto.
"""

import pathlib
from typing import Any

import jinja2
import yaml

from scripts import env

path_here = pathlib.Path(__file__).resolve().parent
path_templates = path_here / "jinja-templates"


def load_data():
    with open(env.BLOG / "resume" / "resume.yaml", "r") as file:
        data = yaml.safe_load(file)

    return data


def render(data: dict[str, Any]):
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("scripts", directory=env.TEMPLATES),
        autoescape=jinja2.select_autoescape(),
    )
    template = env.get_template("test.j2")
    template.render(data)
    print(template.render(data))


def main():
    data = load_data()
    render(data)


if __name__ == "__main__":
    main()
