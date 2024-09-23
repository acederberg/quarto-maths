import pytest


# NOTE: This can be solved using quicksort with a strange metric. I will come
#       back later once I have reviewed.
class Solution:
    def isBigger(self, a: int, b: int, *, memo: dict[int, str]):
        aa, bb = memo[a], memo[b]

        return aa + bb > bb + aa

    def _partition(
        self,
        arr: list[int],
        start: int,
        stop: int,
        memo: dict[int, str],
    ):

        pivot = arr[stop]
        jj = start - 1

        for kk in range(start, stop):
            if self.isBigger(arr[kk], pivot, memo=memo):
                jj += 1
                arr[jj], arr[kk] = arr[kk], arr[jj]

        jj += 1
        arr[jj], arr[stop] = arr[stop], arr[jj]
        return jj

    def quicksort(
        self,
        arr: list[int],
        start: int,
        stop: int,
        memo: dict[int, str],
    ):
        if start < stop:
            jj = self._partition(arr, start=start, stop=stop, memo=memo)

            self.quicksort(arr, start=start, stop=jj - 1, memo=memo)
            self.quicksort(arr, start=jj + 1, stop=stop, memo=memo)

    def largestNumber(self, nums: list[int]) -> str:

        memo = {n: str(n) for n in nums}
        n = len(nums)
        self.quicksort(nums, start=0, stop=n - 1, memo=memo)
        if nums[0] == 0:
            return "0"
        return "".join(memo[k] for k in nums)


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "nums, answer",
    (
        # ([10, 2], "210"),
        ([3, 30, 34, 5, 9], "9534330"),
        ([10, 2, 9, 39, 17], "93921710"),
        ([0, 0], "0"),
    ),
)
def test_solution(solution: Solution, nums: list[int], answer: str):

    answer_computed = solution.largestNumber(nums)
    print(answer_computed, answer)
    assert answer_computed == answer
