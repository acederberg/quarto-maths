"""Too slow. 

The telescoping method has quadratic time complexity, which is less than 
desirable.
"""

import pytest


class Solution:
    def _maxSubArray(
        self,
        arr: list[int],
        *,
        stop: int,
        start: int,
    ):
        # print("->", start, stop)

        total = sum(arr[start:stop])
        if start == stop - 1:
            return start, stop, total

        best_sum = total
        best_stop = stop
        best_start = start

        current = 0

        for k in range(start, stop - 1):

            v = arr[k]

            current += v
            current_refl = total - current

            if current < current_refl:
                opt_sum, opt_start, opt_stop = current_refl, k + 1, stop
            else:
                opt_sum, opt_start, opt_stop = current, start, k

            if opt_sum > best_sum:
                best_sum = opt_sum
                best_stop = opt_stop
                best_start = opt_start

        return best_start, best_stop, best_sum

    def maxSubArrayInfo(self, arr: list[int]):

        best_sum = None
        best_stop = 0
        best_start = 0

        start = 0
        stop = len(arr)

        while start < stop:
            round_start_best, round_stop_best, round_sum_best = self._maxSubArray(
                arr, start=start, stop=stop
            )

            if best_sum is None or round_sum_best >= best_sum:
                best_sum = round_sum_best
                best_start = round_start_best
                best_stop = round_stop_best

            start += 1
            stop -= 1

        if best_start == best_stop:
            best_stop += 1

        return arr[best_start:best_stop], best_sum

    def maxSubArray(self, arr: list[int]):
        _, total = self.maxSubArrayInfo(arr)
        return total


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, answer",
    (
        ([-2, -1], [-1]),
        ([1, -1], [1]),
        ([-2], [-2]),
        ([-20, 4, 3, -1, 5, 8, -10], [4, 3, -1, 5, 8]),
        ([-2, 1, -3, 4, -1, 2, 1, -5, 4], [4, -1, 2, 1]),
        ([1], [1]),
        ([5, 4, -1, 7, 8], [5, 4, -1, 7, 8]),
    ),
)
def test_bigest_sum(solution: Solution, question: list[int], answer: list[int]):
    answer_from_solution, _ = solution.maxSubArrayInfo(question)
    assert answer_from_solution == answer
