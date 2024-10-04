import pathlib

import pytest
import yaml

from dsa.leetcode.longest_pfx import TrieNode


# start snippet solution_initial
class SolutionInitial:

    def sumPrefixScores(self, words: list[str]) -> list[int]:

        def countOne(pfx: str, *, node: TrieNode | None = None) -> int:
            """Count for a specific prefix."""

            if pfx in memo:
                return memo[pfx]

            # NOTE: Traverse until prefix is done. If the prefix cannot be
            #       traversed through, then no words start with the prefix.
            if node is None:
                node = root
                for char in pfx:
                    if char not in node.children:
                        memo[pfx] = 0
                        return 0

                    node = node.children[char]

            # NOTE: If the current node is a terminating node, then one word
            #       is matched.
            count = 0
            if node.terminates:
                count += node.terminates

            # NOTE: Count the number of terminating nodes bellow path. This
            #       should be the sum for each subtree.
            for char in node.children:
                count += countOne(pfx + char, node=node.children[char])

            memo[pfx] = count
            return count

        memo: dict[str, int] = dict()
        root = TrieNode(dict())
        for word in words:
            root.insert(word)

        out = []
        for word in words:
            count = 0
            for end in range(len(word), 0, -1):
                count += countOne(word[:end])

            out.append(count)

        return out
        # end snippet solution_initial


# start snippet solutiond
class Solution:

    def sumPrefixScores(self, words: list[str]) -> list[int]:
        root = TrieNode(dict())
        for word in words:

            node = root
            for char in word:

                if char not in node.children:
                    new_node = TrieNode(dict(), terminates=1)
                    node.children[char] = new_node
                    node = new_node
                else:
                    node = node.children[char]
                    node.terminates += 1

        def count_path(word: str):
            node = root
            count = 0
            for char in word:
                node = node.children[char]
                count += node.terminates

            return count

        return [count_path(word) for word in words]
        # end snippet solutiond


with open(pathlib.Path(__file__).resolve().parent / "cases.yaml") as file:
    cases = list(item.values() for item in yaml.safe_load(file))


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize("words, answer", cases)
def test_solution(solution: Solution, words: list[str], answer: list[int]):

    answer_computed = solution.sumPrefixScores(words)
    print(answer_computed)
    assert answer == answer_computed
