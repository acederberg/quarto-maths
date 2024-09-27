import pytest


# start snippet solution
class MyCalendar:

    def __init__(self):
        self.starts = list()
        self.ends = list()
        self.count = 0

    def closest_left_neighbor(self, start: int) -> int:

        r_start, r_stop = 0, self.count
        r_middle = -1
        while r_start < r_stop - 1:
            r_middle = (r_start + r_stop) // 2
            middle = self.ends[r_middle]
            if start < middle:
                r_stop = r_middle
            else:
                r_start = r_middle

        return min(r_start, r_stop)

    def book(self, start: int, end: int) -> bool:
        if self.count == 0:
            pos = 0
        # NOTE: If start is after all ends, proceed.
        elif self.ends[-1] <= start:
            pos = self.count
        # NOTE: If end is before all starts, proceed.
        elif self.starts[0] >= end:
            pos = 0
        else:

            after_index = self.closest_left_neighbor(start)
            pos = after_index + 1
            if start < self.ends[after_index]:
                return False
            elif pos < self.count and end > self.starts[pos]:
                return False

        self.count += 1
        self.starts.insert(pos, start)
        self.ends.insert(pos, end)
        return True
        # end snippet solution


@pytest.fixture()
def solution():
    return MyCalendar()


@pytest.mark.parametrize(
    "question, find, answer",
    (
        ([10, 20, 25, 30, 33, 40, 49, 50, 54, 60, 53, 70, 72, 80, 81, 82], 71, 70),
        ([1, 7, 15, 31, 63, 127, 255], 16, 15),
        ([1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144], 88, 55),
        ([1], 2, 1),
        ([1, 2], 3, 2),
    ),
)
def test_closest_left_neighbor(question: list[int], find: int, answer: int):

    (solution := MyCalendar()).ends = question
    solution.count = len(question)

    answer_computed = question[solution.closest_left_neighbor(find)]
    assert answer_computed == answer


@pytest.mark.parametrize(
    "question, answer",
    (
        (
            [[10, 20], [15, 25], [20, 30]],
            [True, False, True],
        ),
        (
            [
                [10, 20],
                [20, 30],
                [35, 45],
                [45, 55],
                [30, 40],
                [40, 60],
                [0, 10],
                [0, 10],
                [60, 70],
            ],
            [True, True, True, True, False, False, True, False, True],
        ),
    ),
)
def test_solution(
    solution: MyCalendar,
    question: list[tuple[int, int]],
    answer: list[bool],
):

    for (start, stop), aa in zip(question, answer):

        print("============================")
        aa_computed = solution.book(start, stop)
        print(start, stop, aa_computed, aa)
        assert aa_computed == aa


# Your MyCalendar object will be instantiated and called as such:
# obj = MyCalendar()
# param_1 = obj.book(start,end)
