import json
import random

import pytest

from dsa.bst import Node
from tests.conftest import ASSETS, STASHKEY_TREE_KEYS


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


@pytest.mark.parametrize("tree", STASHKEY_TREE_KEYS, indirect=["tree"])
def test_approximate(tree: Node):

    # NOTE: Make ints, remove root value.
    has = map(
        lambda item: item.value,
        filter(lambda item: item.value != tree.value, tree),
    )
    answers = sorted(has, key=lambda item: abs(item - 500))

    assert tree.value not in answers

    def gen_solution():
        size = tree.size()
        while size > 1:
            assert size == tree.size()

            soln = tree.approximate(500)
            if soln.value == tree.value:
                break

            yield soln.value

            if tree.pop(soln.value) is None:
                raise ValueError(f"Could not pop ``{soln.value}``.")

            size -= 1

    soln = list(gen_solution())
    assert answers[: len(soln)] == soln


@pytest.mark.parametrize("tree", STASHKEY_TREE_KEYS, indirect=["tree"])
def test_min(tree: Node):
    answers = sorted(
        map(
            lambda item: item.value,
            filter(lambda item: item.value != tree.value, tree),
        )
    )
    assert tree.value not in answers

    def gen_solution():
        size = tree.size()
        while size > 1:
            assert size == tree.size()

            soln = tree.min()
            if soln.value == tree.value:
                break

            yield soln.value

            if tree.pop(soln.value) is None:
                raise ValueError(f"Could not pop ``{soln.value}``.")

            size -= 1

    soln = list(gen_solution())
    assert answers[: len(soln)] == soln


# NOTE: Tree is not bst.
def test_iter_bredth():
    with open(ASSETS / "bt-bfs-ordered.json") as file:
        root = Node.from_dict(json.load(file))

    assert list(map(lambda item: item.value, root.iter_bredth())) == list(range(1, 16))


@pytest.mark.parametrize("tree", STASHKEY_TREE_KEYS, indirect=["tree"])
def test_depth(tree: Node):

    layers = list(tree.iter_layers())
    layers.reverse()

    # Since leaves are removed on every iteration, every node should be a leaf.
    depth_bft_last = len(layers)

    for depth_bft, layer in layers:
        if depth_bft == 1:
            break

        for node in layer:
            assert node.left is None and node.right is None
            assert tree.pop(node.value) is not None

        depth_dfs = tree.depth()
        assert depth_bft == depth_dfs
        assert depth_bft == depth_bft_last - 1

        depth_bft_last = depth_bft
