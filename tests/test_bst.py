import random

import pytest

from dsa.bst import Node
from tests.conftest import STASHKEY_TREE_KEYS


def test_basic():
    root = Node(115)
    assert root.left is None and root.right is None and root.value == 115
    assert root.size() == 1

    left = root.add(10)
    assert root.left is not None and root.left.value == 10
    assert root.right is None and root.value == 115
    assert root.left == left
    assert root.size() == 2

    left = root.add(5)
    assert root.right is None
    assert root.left.value == 10
    assert root.left.left is not None and root.left.left.value == 5
    assert root.left.left == left
    assert root.size() == 3

    right = root.add(120)
    assert root.right is not None and root.right.value == 120
    assert root.right == right
    assert root.size() == 4

    has = {115, 10, 5, 120}
    for _ in range(10):
        node = root.add(value := random.randint(0, 1000))

        assert node.value == value
        has.add(node.value)

        assert root.size() == len(has)

    for value in range(1, 1000):
        if value in has:
            assert (node := root.find(value)) is not None
            assert node.value == value

            if node.left is not None:
                assert node.left.value < value
            if node.right is not None:
                assert node.right.value > value
        else:
            assert root.find(value) is None

    assert set(map(lambda item: item.value, root)) == has


def test_approximate_simple():

    node = Node(
        2,
        left=Node(1),
        right=Node(
            5,
            right=Node(
                7,
                left=Node(6),
                right=Node(
                    8,
                    left=Node(9),
                    right=Node(13),
                ),
            ),
        ),
    )
    ans = node.approximate(12)
    assert ans.value == 13


@pytest.mark.parametrize("tree", STASHKEY_TREE_KEYS, indirect=["tree"])
def test_find_parent(tree):

    tree_has = list(map(lambda item: item.value, tree))

    while len(tree_has):
        value = random.choice(tree_has)
        tree_has.remove(value)

        node_parent = tree.find(value, parent=True)

        if value == tree.value:
            assert node_parent is None
            continue

        assert node_parent is not None

        node = tree.find(value, parent=False)
        assert node is not None
        assert node_parent.value != node.value


@pytest.mark.parametrize("tree", STASHKEY_TREE_KEYS, indirect=["tree"])
def test_pop(tree):
    tree = Node.mk(100).check()
    tree_has = list(map(lambda item: item.value, tree))
    tree_has.remove(tree.value)

    size = tree.size()

    while len(tree_has):
        pop_value = random.choice(tree_has)
        tree.pop(pop_value)
        assert tree.find(pop_value) is None

        tree_has.remove(pop_value)
        tree.check()

        assert tree.size() == size - 1

        size -= 1


@pytest.mark.parametrize("_", range(10))
def test_approximate(_):

    root = Node.mk(100)
    has = sorted(map(lambda item: item.value, root))
    ans = min(has, key=lambda item: abs(item - 500))

    soln = root.approximate(500)
    assert abs(ans - 500) == abs(soln.value - 500)


def test_min():
    root = Node.mk(100).check()
    root_has = sorted(map(lambda item: item.value, root))

    root_min_ez = root_has[0]
    root_min = root.min()
    assert root_min is not None
    assert root_min_ez == root_min.value
