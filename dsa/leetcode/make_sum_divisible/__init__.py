import pytest


# start snippet trivial 
class SolutionTrivial:
    def minSubarray(self, nums: list[int], p: int) -> int:

        total = sum(nums)
        n = len(nums)
        total_remainder = total % p
        if total_remainder == 0:
            return 0

        best = n
        for k in range(n):
            s =0 
            for j in range(k, n):

                s += nums[j]
                if s % p == total_remainder and j + 1  - k < best:
                    best = j + 1 - k 

        return best
        # end snippet trivial 


# start snippet solution
class Solution:
    def minSubarray(self, nums: list[int], p: int) -> int:
        total, n = sum(nums), len(nums)

        target = total % p
        if target == 0:
            return 0

        out = n
        mem = {0: -1}
        s = 0

        for k in range(n):

            s = (s + nums[k]) % p
            needed = ( s - target ) % p
            if needed in mem:
                out = min(out, k - mem[needed]) 

            mem[s] = k

        return -1 if out == n else out
        # end snippet solution


@pytest.fixture
def solution(): return Solution()



@pytest.mark.parametrize(
    "question_nums, question_p, answer",
    (
        ([3, 1,  4, 2], 6, 1),
        ([6,3,5,2], 9, 2),
        ([1, 2, 3], 3, 0),
    ),
)
def test_solution(solution: SolutionTrivial, question_nums: list[int], question_p: int, answer: int):

    answer_computed = solution.minSubarray(question_nums, question_p)
    assert answer == answer_computed
