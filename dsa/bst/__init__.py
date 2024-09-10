import json
import random
import secrets
from typing import Any

import pytest
from typing_extensions import Iterator, Self


class Node:
    left: Self | None
    right: Self | None
    value: int
    identity: str

    def __init__(
        self,
        value: int,
        *,
        left: Self | None = None,
        right: Self | None = None,
        identity: str | None = None,
    ):
        self.left = left
        self.right = right
        self.value = value
        self.identity = identity if identity is not None else secrets.token_hex(8)

    @classmethod
    def mk(cls, max_size: int, *, value_max: int = 1000, value_min: int = 0) -> Self:

        root = cls(random.randint(value_min, value_max))
        for _ in range(max_size):
            root.add(random.randint(value_min, value_max))

        return root

    def __iter__(self) -> Iterator[Self]:
        yield self
        if self.left is not None:
            yield from self.left.__iter__()
        if self.right is not None:
            yield from self.right.__iter__()

    def dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"value": self.value}
        if self.right is not None:
            out["right"] = self.right.dict()
        if self.left is not None:
            out["left"] = self.left.dict()

        return out

    def json(self):
        return json.dumps(self.dict(), indent=2)

    def add(self, value: int) -> Self:
        if value < self.value:
            if self.left is None:
                self.left = self.__class__(value)
                return self.left

            return self.left.add(value)
        elif value > self.value:
            if self.right is None:
                self.right = self.__class__(value)
                return self.right
            return self.right.add(value)
        else:
            return self

    def check(self) -> Self:
        """Assess integrity of the bst."""
        for node in self:
            if node.left is not None:
                assert node.left.value < node.value
            if node.right is not None:
                assert node.right.value > node.value
        return self

    # NOTE: This is done from intuition, but it would appear to work.
    def pop(self, value: int) -> Self | None:
        """Remove a value from the tree."""

        if (node_parent := self.find(value, parent=True)) is None:
            return None

        node = node_parent.find(value)
        if node is None:
            raise ValueError("Found parent of node but no node.")

        if node_parent.left == node:
            node_parent.left = None
        else:
            node_parent.right = None

        if (left := node.left) is not None:
            left_new = self.add(left.value)
            left_new.right, left_new.left = left.right, left.left
        if (right := node.right) is not None:
            right_new = self.add(right.value)
            right_new.right, right_new.left = right.right, right.left

        return node

    def find(
        self, value: int, *, parent: bool = False, _prev: Self | None = None
    ) -> Self | None:
        """Find a value in the tree. Use ``parent`` to return the parent node."""

        if value < self.value:
            if self.left is None:
                return None
            return self.left.find(value, _prev=self, parent=parent)
        elif value > self.value:
            if self.right is None:
                return None
            return self.right.find(value, _prev=self, parent=parent)
        else:
            if parent:
                return _prev
            else:
                return self

    def _size(self, count: int = 0):

        count += 1  # count self
        if self.left is not None:
            count = self.left._size(count)
        if self.right is not None:
            count = self.right._size(count)

        return count

    def size(self) -> int:
        """Compute the size of the tree."""
        return self._size()

    def min(self) -> Self | None:
        """Minimum should be the leftmost node on the tree.

        Obviously, we could just use ``__iter__`` and take the minimum of
        some sequence, but this is certainly less efficient.
        """

        if self.left:
            return self.left.min()
        else:
            return self

    # Is there a more clever way to do this? This is basically
    # https://medium.com/journey-to-becoming-an-algoat/closest-value-in-a-bst-with-recursion-16bf90ad3bc2
    def approximate(self, value: int) -> Self:
        best: Node = self
        diff_best = None

        for node in self:
            if not (diff := abs(node.value - value)):
                best = node
                break

            if diff_best is None or diff_best > diff:
                best = node
                diff_best = diff

        return best
