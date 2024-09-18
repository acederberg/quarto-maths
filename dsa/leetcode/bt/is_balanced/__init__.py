from typing import Any

import pytest

from dsa.leetcode.bt.from_desc import TreeNode

# NOTE: https://leetcode.com/problems/balanced-binary-tree/description/
# NOTE: https://leetcode.com/problems/binary-tree-inorder-traversal/description/
# NOTE: https://leetcode.com/problems/balance-a-binary-search-tree/editorial/


# start snippit solution_initial
class SolutionInitial:
    def _isBalanced(
        self, root: TreeNode | None, *, _depth: int = 0
    ) -> tuple[bool, int]:
        if root is None:
            return True, _depth

        left_is_balanced, left_depth = self._isBalanced(root.left, _depth=_depth + 1)
        right_is_balanced, right_depth = self._isBalanced(root.right, _depth=_depth + 1)

        self_is_balanced = (
            abs(left_depth - right_depth) <= 1
            and right_is_balanced
            and left_is_balanced
        )
        depth = max(left_depth, right_depth)

        return self_is_balanced, depth

    def isBalanced(self, root: TreeNode | None) -> bool:
        is_balanced, _ = self._isBalanced(root)
        return is_balanced

    # end snippit solution_final


# start snippit solution
class Solution:
    def _isBalanced(self, root: TreeNode | None, *, _depth: int = 0) -> int:
        if root is None:
            return _depth

        _depth += 1
        left_depth = self._isBalanced(root.left, _depth=_depth)
        if left_depth < 0:
            return -1

        right_depth = self._isBalanced(root.right, _depth=_depth)
        if right_depth < 0:
            return -1

        if abs(left_depth - right_depth) > 1:
            return -1

        return max(left_depth, right_depth)

    def isBalanced(self, root: TreeNode | None) -> bool:
        return self._isBalanced(root) >= 0

    # end snippit solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, is_balanced",
    (
        ({"value": 1}, True),
        (
            {
                "value": 1,
                "right": {
                    "value": 2,
                    "right": {
                        "value": 3,
                    },
                },
            },
            False,
        ),
        (
            {
                "value": 2,
                "right": {"value": 3},
                "left": {"value": 1},
            },
            True,
        ),
        (
            {
                "value": 1,
                "left": {"value": 2},
                "right": {
                    "value": 4,
                    "left": {
                        "value": 5,
                        "right": {"value": 6},
                        "left": {"value": 7},
                    },
                    "right": {"value": 8},
                },
            },
            False,
        ),
    ),
)
def test_solution_is_balanced(
    solution: Solution, question: dict[str, Any], is_balanced: bool
):

    question_tree = TreeNode.fromDict(question)
    is_balanced_computed = solution.isBalanced(question_tree)
    print(is_balanced_computed, is_balanced)
    assert is_balanced_computed == is_balanced
