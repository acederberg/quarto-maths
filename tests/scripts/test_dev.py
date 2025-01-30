import pathlib

import pytest

from acederbergio import env
from acederbergio.api import quarto


def test_ignore_node():
    node = quarto.Node(False)

    assert not node.has_prefix(p := "/home/docker/.venv")

    node.add(p)
    assert node.has_prefix(p)
    assert node.has_prefix(q := p + "/bin")
    assert not node.has_prefix("/home/docker")
    assert not node.has_prefix("/home")

    node.add(q)
    assert node.has_prefix(q)
    assert node.has_prefix(q + "/httpx")  # Cannot be link!
    assert not node.has_prefix("/home/docker")

    assert not node.has_prefix("/home")


@pytest.fixture(scope="session")
def filter() -> quarto.Filter:
    context = quarto.Context()
    return quarto.Filter(context)


@pytest.mark.parametrize(
    "case, result",
    (
        # NOTE: Directories are ignored in general, even these ones that are
        #       watched.
        (env.BLOG / "filters", (True, "directory")),
        (env.SCRIPTS / "filters", (True, "directory")),
        (env.BLOG / "includes", (True, "directory")),
        (env.BLOG / "themes", (True, "directory")),
        #
        # NOTE: Ignored directories are ignored.
        (env.BLOG / ".quarto", (True, "explicit")),
        (env.BLOG / "_freeze", (True, "explicit")),
        (env.BUILD / "site_libs", (True, "explicit")),
        (env.ROOT / ".git", (True, "explicit")),
        #
        # NOTE: These should not be ignored.
        (env.SCRIPTS / "filters/floaty.py", (False, None)),
        (env.SCRIPTS / "filters/__init__.py", (False, None)),
        (env.BLOG / "includes/live.js", (False, None)),
        (env.BLOG / "themes/terminal.scss", (False, None)),
        (env.BLOG / "filters/floaty.py", (False, None)),
        (env.BLOG / "resume/templates/template.tex", (False, None)),
        #
        # NOTE: These should be ignored.
        # (env.SCRIPTS / "filters/__pycache__/floaty.pyc", False),
        (env.BUILD / "index.html", (True, "explicit")),
        (env.ROOT / ".quarto/foo.bar", (True, "suffix=.bar")),
        (env.SCRIPTS / "api" / "__init__.py", (True, "explicit")),
        #
        # NOTE: These have bad extensions.
        (env.BLOG / "index.ts", (True, "suffix=.ts")),
        (env.ROOT / "foo.go", (True, "suffix=.go")),
    ),
)
def test_context(filter: quarto.Filter, case: pathlib.Path, result: tuple[bool, str]):
    assert filter.is_ignored(case) == result
