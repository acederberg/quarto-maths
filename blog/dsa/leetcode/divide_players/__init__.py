import pytest


# start snippet solution
class Solution:

    # NOTE: Skill has positive elements and even length.
    def dividePlayers(self, skill: list[int]) -> int:

        s, n = sum(skill), len(skill)
        n2 = n // 2

        # NOTE: Must be divisible by n.
        if s % n2:
            return -1

        # NOTE: Memo maps completions to their index in ``skill``.
        target = s // n2
        memo: dict[int, int] = {}

        out = 0
        for val in skill:

            if (diff := target - val) <= 0:
                return -1
            elif val in memo:
                memo[val] -= 1
                out += val * diff

                if memo[val] == 0:
                    memo.pop(val)

            elif diff not in memo:
                memo[diff] = 1
            else:
                memo[diff] += 1

        if memo:
            return -1

        return out
        # end snippet solution


# start snippet sort
class SolutionSort:

    def dividePlayers(self, skill: list[int]) -> int:

        skill.sort()
        n = len(skill)
        target = skill[0] + skill[n - 1]

        out = 0
        for k in range(n // 2):
            j = n - 1 - k
            a, b = skill[k], skill[j]

            if a + b != target:
                return -1

            out += a * b

        return out
        # end snippet sort


@pytest.fixture
def solution():
    return SolutionSort()


@pytest.mark.parametrize(
    "question, answer",
    (
        ([3, 2, 5, 1, 3, 4], 22),
        ([3, 4], 12),
        ([1, 1, 2, 3], -1),
        ([2, 1, 5, 2], -1),
        ([2, 3, 4, 2, 5, 5], 32),
        ([10, 14, 16, 15, 9, 4, 4, 4], -1),
    ),
)
def test_solution(
    solution: Solution,
    question: list[int],
    answer: int,
):

    answer_computed = solution.dividePlayers(question)
    assert answer == answer_computed
