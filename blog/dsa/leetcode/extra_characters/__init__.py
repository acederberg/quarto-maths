import pytest


# start snippet solution
class Solution:
    def minExtraChar(self, s: str, dictionary: list[str]) -> int:

        n = len(s)
        dictionary_set = set(dictionary)

        def dp(start: int, memo: dict[int, int]):
            """This function should inspect the substring from ``n`` to its
            end."""

            # NOTE: If the end of the string is reached, there are no remaining
            #       characters.
            if start in memo:
                return memo[start]
            elif start == n:
                return 0

            # NOTE: Assume that start is bad. Count up the remaining
            #       characters and add one for the assumption that the start is
            #       bad.
            out = dp(start + 1, memo) + 1

            for end in range(start, n):
                if s[start : end + 1] in dictionary_set:
                    out_new = dp(end + 1, memo)

                    if out_new < out:
                        out = out_new

            memo[start] = out
            return out

        memo: dict[int, int] = dict()
        return dp(0, memo)
        # end snippet solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, dictionary, answer",
    (
        ("leetscode", ["leet", "code"], 1),
        ("sayhelloworld", ["hello", "world"], 3),
    ),
)
def test_solution(
    solution: Solution, question: str, dictionary: list[str], answer: int
):

    answer_computed = solution.minExtraChar(question, dictionary)
    assert answer == answer_computed
