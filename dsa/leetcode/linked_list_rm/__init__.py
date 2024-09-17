from typing import Optional

import pytest
from typing_extensions import Self


# start snippet node
class ListNode:
    val: int
    next: Self | None

    def __init__(self, val=0, next: Self | None = None):
        self.val = val
        self.next = next

    def __iter__(self):
        curr = self
        while curr is not None:
            yield curr.val
            curr = curr.next

    @classmethod
    def fromItems(cls, *items: int) -> Self:
        if not items:
            raise ValueError("At least one item is required.")

        head = cls(items[0])

        lastnode = head
        for k in range(len(items) - 1):
            item = items[k + 1]
            node = cls(item)
            lastnode.next = node
            lastnode = node

        return head
        # end snippet node


# start snippet solution
class Solution:
    def modifiedList(
        self,
        nums: list[int],
        head: ListNode,
    ) -> Optional[ListNode]:

        hashed = set(nums)

        # NOTE: Remove any heads that have bad values.
        node = head
        nodelast: ListNode  # already checked
        while node is not None:
            if node.val not in hashed:
                break

            nodelast = node
            node = node.next

        head_final = node
        if head_final is None or head_final.next is None:
            return head_final

        # NOTE: Delink if value is bad. ``nodelast`` should not be incremented
        #       when a bad value is removed as it is will remain the same.
        while node is not None:

            if node.val in hashed:
                nodelast.next = node.next
                node = node.next
            else:
                nodelast = node
                node = node.next

        return head_final
        # end snippet solution


# start snippet solution_2
class Solution2:
    def modifiedList(
        self,
        nums: list[int],
        head: ListNode,
    ) -> Optional[ListNode]:

        # NOTE: Remove any heads that have bad values.
        hashed = set(nums)
        head_final = None
        is_head = True
        node = head
        nodelast: ListNode

        while node is not None:
            if is_head:
                if node.val not in hashed:
                    head_final = node
                    is_head = False
                    continue

                nodelast = node
                node = node.next
                nodelast.next = None
            elif node.val in hashed:
                nodelast.next = node.next
                node.next = None

                node = nodelast.next
            else:
                nodelast = node
                node = node.next

        return head_final
        # end snippet solution_2


@pytest.fixture
def solution():
    return Solution2()


@pytest.mark.parametrize(
    "nums, head, answer",
    (
        ([1, 2, 3], [1, 2, 3, 4, 5], [4, 5]),
        ([1], [1, 2, 1, 2, 1, 2], [2, 2, 2]),
        ([1, 7, 6, 2, 4], [3, 7, 1, 8, 1], [3, 8]),
    ),
)
def test_solution(
    solution: Solution,
    nums: list[int],
    head: ListNode,
    answer: ListNode,
):

    input = ListNode.fromItems(*head)

    print(list(input))
    _got = solution.modifiedList(nums, input)
    assert _got is not None

    got = list(_got)
    print(got)
    assert got == answer
