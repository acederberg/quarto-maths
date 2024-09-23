from typing import Any, Iterator

import pytest

from dsa.leetcode.bt.from_desc import TreeNode


# start snippet solution_trivial
class SolutionTrivial:
    def _inorderTraversal(self, root: TreeNode) -> Iterator[int]:

        if root.left is not None:
            yield from self._inorderTraversal(root.left)
        yield root.val
        if root.right is not None:
            yield from self._inorderTraversal(root.right)

    def inorderTraversal(self, root: TreeNode | None) -> list[int]:
        if root is None:
            return list()

        return list(self._inorderTraversal(root))

        # end snippet solution_trivial


# start snippet solution_trivial_improved
class SolutionTrivial2:
    def _inorderTraversal(self, root: TreeNode, nodes: list[int]):

        if root.left is not None:
            self._inorderTraversal(root.left, nodes)

        nodes.append(root.val)

        if root.right is not None:
            self._inorderTraversal(root.right, nodes)

    def inorderTraversal(self, root: TreeNode | None) -> list[int]:
        vals = list()
        if root is None:
            return vals

        self._inorderTraversal(root, vals)
        return vals

        # end snippet solution_trivial_improved


# start snippet solution_nontrivial
class Solution:
    def _inorderTraversal(self, root: TreeNode):

        stack = []
        node = root
        while stack or node is not None:
            # If left is found, keep going left
            while node is not None:
                stack.append(node)
                node = node.left

            # When no left is found, yield value. Node is ``None`` so use the
            # top of the stack.
            node = stack.pop()
            yield node.val

            # Now that the top of the stack has been used, this will be added
            # to the stack in the nested ``while`` loop.
            node = node.right

    def inorderTraversal(self, root: TreeNode | None):
        if root is None:
            return list()

        return list(self._inorderTraversal(root))

        # end snippet solution_nontrivial


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "tree, answer",
    (
        ({"value": 1, "right": {"value": 2, "left": 3}}, [1, 3, 2]),
        (
            {
                "value": 1,
                "left": {
                    "value": 2,
                    "left": 4,
                    "right": {"value": 5, "left": 6, "right": 7},
                },
                "right": {
                    "value": 3,
                    "right": {
                        "value": 8,
                        "left": 9,
                    },
                },
            },
            [4, 2, 6, 5, 7, 1, 3, 9, 8],
        ),
        ({"value": 1}, [1]),
        (None, []),
    ),
)
def test_solution(solution: Solution, tree: dict[str, Any], answer: list[int]):

    root = TreeNode.fromDict(tree)
    answer_computed = solution.inorderTraversal(root)
    print(answer_computed)
    print(answer)
    assert answer == answer_computed
