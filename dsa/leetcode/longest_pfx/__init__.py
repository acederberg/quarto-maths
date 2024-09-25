from typing import Any

import pytest
from typing_extensions import Self


# start snippet solution_trivial
class SolutionTrivial:

    def pfx_elems(self, a: str, b: str) -> int:

        count = 0
        for char_a, char_b in zip(a, b):
            if char_a != char_b:
                break

            count += 1

        return count

    def longestCommonPrefix(self, arr1: list[int], arr2: list[int]) -> int:

        size_biggest = 0

        for a in map(str, sorted(arr1, reverse=True)):
            if len(a) <= size_biggest:
                break

            for b in map(str, arr2):
                size = self.pfx_elems(a, b)
                if size > size_biggest:
                    size_biggest = size

        return size_biggest
        # end snippet solution_trivial


# start snippet trie
# start snippet trie_min
class TrieNode:
    terminates: int
    children: dict[str, Self]

    def __init__(
        self,
        children: dict[str, Self],
        terminates: int = False,
    ):
        self.children = children
        self.terminates = terminates

    # end snippet trie_min

    def toDict(self, depth=None, *, _depth: int = 0) -> dict[str, Any]:

        out: dict[str, Any] = dict()

        if self.terminates:
            out["terminates"] = self.terminates

        if depth is None or _depth < depth:
            out.update(
                {
                    char: node.toDict(depth, _depth=_depth + 1)
                    for char, node in self.children.items()
                }
            )
        return out

    def insert(self, val: str):

        node = self
        for char in val:
            if char not in node.children:
                node_new = self.__class__(dict())
                node.children[char] = node_new
                node = node_new
            else:
                node = node.children[char]

        node.terminates += 1
        return

    def get(self, val: str) -> Self | None:
        node = self
        for char in val:
            if char not in node.children:
                return None
            node = node.children[char]

        return node

    def prefix(self, val: str) -> int:

        node, pfx = self, 0

        for char in val:
            if char not in node.children:
                return pfx

            pfx += 1
            node = node.children[char]

        return pfx
        # end snippet trie


# start snippet solution
class Solution:
    def longestCommonPrefix(self, arr1: list[int], arr2: list[int]) -> int:
        root = TrieNode(dict())

        for s in map(str, arr1):
            root.insert(s)

        size_max = 0

        arr2.sort(reverse=True)
        for s in map(str, arr2):
            if len(s) <= size_max:
                break

            size = root.prefix(s)
            size_max = max(size, size_max)

        return size_max
        # end snippet soltion


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "arr1, arr2, answer",
    (
        ([1, 10, 100], [1000], 3),
        ([1, 2, 3], [4, 4, 4], 0),
    ),
)
def test_solution(solution: Solution, arr1: list[int], arr2: list[int], answer: int):

    answer_computed = solution.longestCommonPrefix(arr1, arr2)
    assert answer == answer_computed


def test_trie():

    root = TrieNode(dict())
    assert not root.get("a")

    root.insert("a")
    assert root.contains("a")
    assert "a" in root.children
    assert not len(root.children["a"].children)

    root.insert("aardvark")
    root.insert("alameda")
    root.insert("alphabetical")

    assert root.contains("a") and root.contains("aardvark")
    assert root.contains("alameda") and root.contains("alphabetical")
    assert not root.contains("aa") and not root.contains("al")

    assert root.prefix("alaverga") == "ala"
    assert root.prefix("aa") == "aa"
