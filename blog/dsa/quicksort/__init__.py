import pytest


class Solution:
    def quicksort_partition(self, arr: list[int], start: int, stop: int):
        pivot = arr[stop]
        ii = start - 1

        for kk in range(start, stop):
            if arr[kk] <= pivot:
                ii += 1
                arr[kk], arr[ii] = arr[ii], arr[kk]

        arr[ii + 1], arr[stop] = arr[stop], arr[ii + 1]

        return ii + 1

    def _quicksort(
        self,
        arr: list[int],
        *,
        start: int,
        stop: int,
    ):
        if start < stop:
            pivot_index = self.quicksort_partition(arr, start, stop)

            self._quicksort(arr, start=start, stop=pivot_index - 1)
            self._quicksort(arr, start=pivot_index + 1, stop=stop)

    def quicksort(self, arr: list[int]):
        return self._quicksort(arr, start=0, stop=len(arr) - 1)


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, answer",
    (
        ([2, 3, 1], [1, 2, 3]),
        ([5, 1, 4, 3, 2], [1, 2, 3, 4, 5]),
        ([10, 9, 1, 2, 8, 7, 3, 4, 6, 5], list(range(1, 11))),
    ),
)
def test_solution(
    solution: Solution,
    question: list[int],
    answer: list[int],
):
    solution.quicksort(question)
    assert question == answer
