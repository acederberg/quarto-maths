import pytest

# 00:00, 00:30, 00:31, 12:30, 01:20

minutes_total = 1440


# start snippet solution
class Solution:
    def evalBest(self, minutes_previous: int, minutes_current: int):
        diff = minutes_current - minutes_previous
        diff = min(diff, minutes_total - diff)
        return diff

    def findMinDifference(self, timePoints: list[str]) -> int:

        visited = set()
        parsed = dict()

        for tp in timePoints:
            # NOTE: ensures constant time.
            if tp in visited:
                return 0

            visited.add(tp)

            str_hrs, str_mins = tp.split(":")
            minutes = (int(str_hrs) * 60) + int(str_mins)
            parsed[minutes] = tp

        # NOTE: Iterate parsed in order. This will take constant time since
        #       there are at most 1440 keys.
        diff_best = minutes_total
        minutes_previous = None
        minutes_first = None

        for minutes in range(minutes_total):
            if minutes not in parsed:
                continue
            elif minutes_previous is None:
                minutes_previous = minutes
                minutes_first = minutes
                continue

            minutes_current = minutes
            if diff_best > (diff := self.evalBest(minutes_previous, minutes_current)):
                diff_best = diff

            minutes_previous = minutes_current

        # NOTE: Order matters since ``abs`` is not applied.
        # NOTE: Compare the first and final entries since the will not be
        #       compared in the above loop.
        if diff_best > (diff := self.evalBest(minutes_first, minutes_current)):  # type: ignore
            diff_best = diff

        return diff_best
        # end snippet solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "timePoints, answer",
    (
        (["23:59", "00:00"], 1),
        (["00:00", "23:59", "00:00"], 0),
        (["01:01", "01:12", "12:45", "3:14", "3:59", "23:22"], 11),
        (["12:12", "00:13"], 719),
        (["00:00", "04:00", "22:00"], 120),
    ),
)
def test_solution(solution: Solution, timePoints: list[str], answer: int):

    assert solution.findMinDifference(timePoints) == answer
