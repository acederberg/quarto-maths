import secrets

import pytest

from dsa.bst import Node

STASHKEY_TREE = pytest.StashKey[dict[str, Node]]()
STASHKEY_TREE_KEYS = list(secrets.token_hex(8) for _ in range(10))


def pytest_configure(config: pytest.Config):
    # NOTE: This is added so that data structures can be stored and  recovered
    #       in IPython.
    config.stash[STASHKEY_TREE] = dict()


@pytest.fixture
def tree(pytestconfig: pytest.Config, request: pytest.FixtureRequest) -> Node:
    key = request.param
    trees = pytestconfig.stash[STASHKEY_TREE]
    root = Node.mk(100).check()
    trees[key] = root

    return root.check()
