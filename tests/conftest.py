import secrets

import pytest

from dsa.bst import Node

STASHKEY_TREE = pytest.StashKey[dict[str, Node]]()
STASHKEY_TREE_KEYS = list(secrets.token_hex(8) for _ in range(10))


def pytest_configure(config):
    config.stash[STASHKEY_TREE] = dict()


@pytest.fixture
def tree(pytestconfig: pytest.Config, request: pytest.FixtureRequest) -> Node:
    key = request.param
    trees = pytestconfig.stash[STASHKEY_TREE]
    if key not in trees:
        root = Node.mk(100).check()
    else:
        root = trees[key]

    return root.check()
