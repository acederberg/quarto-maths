import pytest
import heapq


class SolutionTLE:

    def smallestChair(self, times: list[list[int]], targetFriend: int) -> int:

        occupied: dict[int, int] = {}
        last_time = -1

        final = 0
        opened = set()

        for pos, (time, vacates) in sorted(
            enumerate(times), key=lambda items: items[1][0]
        ):
            if time != last_time:
                for k in range(final):
                    if k in occupied and occupied[k] <= time:
                        occupied.pop(k)
                        opened.add(k)

            if opened:
                seat_number = min(opened)
                opened.remove(seat_number)
            else:
                seat_number = final
                final += 1

            if pos == targetFriend:
                return seat_number

            occupied[seat_number] = vacates
            last_time = time

        return -1


# start snippet solution
class SolutionWorks:
    def smallestChair(self, times: list[list[int]], targetFriend: int) -> int:
        occupied: dict[int, int] = {}
        last_time = -1

        final = 0

        for pos, (time, vacates) in sorted(
            enumerate(times), key=lambda items: items[1][0]
        ):
            if time != last_time:
                for k in list(occupied.keys()):
                    if occupied[k] <= time:
                        occupied.pop(k)

            if len(occupied) != final:
                _seat_number = final
                for _seat_number in range(final):
                    if _seat_number not in occupied:
                        break

                seat_number = _seat_number
            else:
                seat_number = final
                final += 1

            if pos == targetFriend:
                return seat_number

            occupied[seat_number] = vacates
            last_time = time

        return -1
        # end snippet solution


# start snippet solution_min_heap
class SolutionMinHeap:

    def smallestChair(self, times: list[list[int]], targetFriend: int) -> int:
        occupied: dict[int, int] = {}
        available = []
        last_time = -1

        final = 0

        for pos, (time, vacates) in sorted(
            enumerate(times), key=lambda items: items[1][0]
        ):
            if time != last_time:
                for k in list(k for k, v in occupied.items() if v <= time):
                    occupied.pop(k)
                    heapq.heappush(available, k)

            if available:
                seat_number = heapq.heappop(available)
            else:
                seat_number = final
                final += 1

            if pos == targetFriend:
                return seat_number

            occupied[seat_number] = vacates
            last_time = time

        return -1
        # end snippet solution_min_heap


# start snippet solution_editorial
class Solution:

    def smallestChair(self, times: list[list[int]], targetFriend: int) -> int:

        events = []
        for index, (time_start, time_stop) in enumerate(times):
            events.append([time_start, index])
            events.append([time_stop, ~index])

        events.sort(key=lambda pair: pair[0])

        vacant = list(range(len(times)))
        occupied = list()

        for time, pos in events:

            # Mark all chairs as vacated for the friends which have left.
            while occupied and occupied[0][0] <= time:
                _, vacated_index = heapq.heappop(occupied)
                heapq.heappush(vacant, vacated_index)

            # Mark chair occupied if the friend is ariving.
            if pos > -1:
                vacant_index = heapq.heappop(vacant)
                heapq.heappush(occupied, (times[pos][1], vacant_index))

                if pos == targetFriend:
                    return vacant_index

        return -1
        # end snippet solution_editorial


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "times, target_friend, answer",
    (
        ([(1, 4), (2, 3), (4, 6)], 1, 1),
        ([(3, 10), (1, 2), (1, 3), (1, 5), (2, 6)], 0, 1),
        ([[3, 10], [1, 5], [2, 6]], 0, 2),
        ([[1, 2], [2, 3]], 1, 0),
        ([[4, 5], [6, 8], [8, 10], [1, 8]], 2, 0),
        ([[7,10],[6,7],[1,3],[2,7],[4,5]], 0, 0),
        ([[99999,100000],[1,2]], 1, 0),
        ([[2,4],[4,9],[3,4],[6,8],[5,10]], 4, 1),
        ([(k, 10000) for k in range(10000) ], 9998, 9998
         )
    ),
)
def test_solution(
    solution: Solution, times: list[tuple[int, int]], target_friend: int, answer: int
):

    answer_computed = solution.smallestChair(times, target_friend)  # type: ignore
    assert answer == answer_computed
