from typing import Any, Iterator

import pytest

from dsa.leetcode.bt import is_balanced
from dsa.leetcode.bt.from_desc import TreeNode


class Solution:
    def _inorderTraversal(self, root: TreeNode) -> Iterator[TreeNode]:

        if root.left is not None:
            yield from self._inorderTraversal(root.left)
        yield root
        if root.right is not None:
            yield from self._inorderTraversal(root.right)

    def balanceBST(self, root: TreeNode) -> TreeNode:
        values = list(self._inorderTraversal(root))

        def _balanceBST(
            start: int,
            stop: int,
        ):
            if start > stop:
                return None

            middle = start + ((stop - start) // 2)
            node = values[middle]
            node.left = _balanceBST(start, middle - 1)
            node.right = _balanceBST(middle + 1, stop)

            return node

        return _balanceBST(0, len(values) - 1)  # type: ignore


class _Solution(Solution, is_balanced.Solution): ...


@pytest.fixture(scope="session")
def solution():
    return _Solution()


@pytest.mark.parametrize(
    "question",
    (
        {"value": 1},
        {"value": 1, "left": {"value": 2, "left": {"value": 3, "left": 4}}},
        {"value": 2, "left": 1, "right": 3},
    ),
)
def test_solution(
    solution: _Solution,
    question: dict[str, Any],
):
    root = TreeNode.fromDict(question)
    assert root is not None

    root_answer = solution.balanceBST(root)

    assert solution.isBalanced(root_answer)
