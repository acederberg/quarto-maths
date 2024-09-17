import pytest


# start snippet solution_trivial
class SolutionTrivial:
    def twoSum(self, nums: list[int], target: int) -> list[int]:

        n = len(nums)
        for k in range(n):
            for j in range(k + 1, n):
                if nums[k] + nums[j] == target:
                    return [k, j]
        return [k, j]
        # end snippet solution_trivial


# start snippet solution
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:

        memo = dict()
        for k, num in enumerate(nums):

            diff = target - num
            if num in memo:
                return [k, memo[num]]

            memo[diff] = k

        raise ValueError("No pair!")
        # end snippet solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "nums, target, answer",
    (
        ([2, 7, 11, 15], 9, [0, 1]),
        ([3, 4, 2], 6, [1, 2]),
        ([3, 3], 6, [0, 1]),
    ),
)
def test_solution(solution: Solution, nums: list[int], target: int, answer: list[int]):
    got = solution.twoSum(nums, target)
    print(got)
    assert sorted(got) == sorted(answer)
