import json
from typing import Any, Optional

import pytest
from typing_extensions import Self


class TreeNode:
    val: int
    left: Self | None
    right: Self | None

    def __init__(
        self,
        val: int = 0,
        left: Self | None = None,
        right: Self | None = None,
    ):
        self.val = val
        self.left = left
        self.right = right

    @classmethod
    def fromDict(cls, values: dict[str, Any] | int | None) -> Self | None:
        if values is None:
            return None
        elif isinstance(values, int):
            return cls(values)

        args = dict(val=values["value"])
        if "left" in values:
            args["left"] = cls.fromDict(values["left"])
        if "right" in values:
            args["right"] = cls.fromDict(values["right"])
        return cls(**args)

    def toDict(self) -> dict[str, Any]:

        serial: dict[str, Any] = dict(value=self.val)
        if self.left is not None:
            serial["left"] = self.left.toDict()
        if self.right is not None:
            serial["right"] = self.right.toDict()

        return serial


# start snippet solution_initial
class SolutionInitial:
    def createBinaryTree(
        self,
        descriptions: list[list[int]],
    ) -> Optional[TreeNode]:

        # NOTE: Works because is tree of unique values.
        nodes = {
            color: (TreeNode(color), (color_parent, color, is_left))
            for color_parent, color, is_left in descriptions
        }

        # NOTE: Linking step. Root should only appear as a parent, and thus
        #       was not constructed in the definition of nodes.
        root = None
        for node, (color_parent, _, is_left) in nodes.values():
            if color_parent not in nodes:
                if root is None:
                    root = TreeNode(color_parent)
                node_parent = root
            else:
                node_parent, _ = nodes[color_parent]

            if is_left:
                node_parent.left = node
            else:
                node_parent.right = node

        return root
        # end snippet solution_initial


# start snippet solution
class SolutionGoodmem:
    def createBinaryTree(
        self,
        descriptions: list[list[int]],
    ) -> Optional[TreeNode]:

        # NOTE: Works because is tree of unique values.
        nodes = {}
        nodes_no_parent = {}
        for color_parent, color, is_left in descriptions:
            node = TreeNode(color)
            nodes[color] = node

            # NOTE: Attach node to parent if found. Otherwise remember that it does
            #       not yet have a parent.
            if color_parent not in nodes:
                if color_parent not in nodes_no_parent:
                    nodes_no_parent[color_parent] = {is_left: node}
                else:
                    nodes_no_parent[color_parent][is_left] = node
            else:
                node_parent = nodes[color_parent]
                if is_left:
                    node_parent.left = node
                else:
                    node_parent.right = node

            # NOTE: If nodes_no_parent needs to link with this node, then do so
            if node.val not in nodes_no_parent:
                continue

            for child_is_left, child in nodes_no_parent[node.val].items():
                if child_is_left:
                    node.left = child
                else:
                    node.right = child

            nodes_no_parent.pop(node.val)

        # There will only be one left.
        for value, items in nodes_no_parent.items():

            root = TreeNode(value)
            if 0 in items:
                root.right = items[0]
            if 1 in items:
                root.left = items[1]

            return root

        return None
        # end snippet solution


# start snippet solution_spoiled
class Solution:
    def createBinaryTree(
        self,
        descriptions: list[list[int]],
    ) -> Optional[TreeNode]:

        # NOTE: Works because is tree of unique values.
        nodes = {}
        children = set()
        for desc in descriptions:
            color_parent, color, is_left = desc
            if color not in nodes:
                node = TreeNode(color)
                nodes[color] = node
            else:
                node = nodes[color]

            # NOTE: Create parent node if not exists.
            if color_parent not in nodes:
                node_parent = TreeNode(color_parent)
                nodes[color_parent] = node_parent
            else:
                node_parent = nodes[color_parent]

            # NOTE: Assign.
            if is_left:
                node_parent.left = node
            else:
                node_parent.right = node

            children.add(color)

        # There will only be one left.
        for value in nodes:
            if value not in children:
                return nodes[value]

        return None
        # end snippet solution_spoiled


@pytest.fixture
def solution():
    return Solution()


cases = (
    (
        [[20, 15, 1], [20, 17, 0], [50, 20, 1], [50, 80, 0], [80, 19, 1]],
        treedict := {
            "value": 50,
            "left": {
                "value": 20,
                "left": {"value": 15},
                "right": {"value": 17},
            },
            "right": {
                "value": 80,
                "left": {"value": 19},
            },
        },
    ),
    (
        [[85, 74, 0], [38, 82, 0], [39, 70, 0], [82, 85, 0], [74, 13, 0], [13, 39, 0]],
        {
            "value": 38,
            "right": {
                "value": 82,
                "right": {
                    "value": 85,
                    "right": {
                        "value": 74,
                        "right": {
                            "value": 13,
                            "right": {"value": 39, "right": {"value": 70}},
                        },
                    },
                },
            },
        },
    ),
)


def test_tree():

    root = TreeNode.fromDict(treedict)
    assert root is not None
    assert root.val == 50

    assert root.toDict() == treedict


@pytest.mark.parametrize("question, answer", cases)
def test_solution(
    solution: Solution,
    question: list[list[int]],
    answer: dict[str, Any],
):

    got = solution.createBinaryTree(question)
    answer_root = TreeNode.fromDict(answer)
    assert answer_root is not None and got is not None

    print("======================================")
    print("answer")
    print(json.dumps(answer_root.toDict(), indent=2))

    print("======================================")
    print("got")
    print(json.dumps(got.toDict(), indent=2))

    assert answer_root is not None
    assert got.toDict() == answer_root.toDict()
