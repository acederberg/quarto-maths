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
        (env.BLOG / "filters", True),
        (env.SCRIPTS / "filters", True),
        (env.BLOG / "includes", True),
        (env.BLOG / "themes", True),
        #
        # NOTE: Ignored directories are ignored.
        (env.BLOG / ".quarto", True),
        (env.BLOG / "_freeze", True),
        (env.BUILD / "site_libs", True),
        (env.ROOT / ".git", True),
        #
        # NOTE: These should not be ignored.
        (env.SCRIPTS / "filters/floaty.py", False),
        (env.SCRIPTS / "filters/__init__.py", False),
        (env.BLOG / "includes/live.js", False),
        (env.BLOG / "themes/terminal.scss", False),
        (env.BLOG / "filters/floaty.py", False),
        (env.BLOG / "resume/templates/template.tex", False),
        #
        # NOTE: These should be ignored.
        # (env.SCRIPTS / "filters/__pycache__/floaty.pyc", False),
        (env.BUILD / "index.html", True),
        (env.ROOT / ".quarto/foo.bar", True),
        (env.SCRIPTS / "api" / "__init__.py", True),
        #
        # NOTE: These have bad extensions.
        (env.BLOG / "index.ts", True),
        (env.BUILD / "foo.go", True),
    ),
)
def test_context(filter: quarto.Filter, case: pathlib.Path, result: bool):
    assert filter.is_ignored(case) is result
