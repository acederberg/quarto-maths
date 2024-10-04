import pytest
import yaml
from kagglehub.gcs_upload import pathlib


def closest_left_neighbor(items: list[int], value: int, *, count: int) -> int:
    """Find the closest left neighbor to start in ends."""

    r_start, r_stop = 0, count
    r_middle = -1
    while r_start < r_stop - 1:
        r_middle = (r_start + r_stop) // 2
        middle = items[r_middle]
        if value < middle:
            r_stop = r_middle
        else:
            r_start = r_middle

    return min(r_start, r_stop)


def is_schedulable(
    starts: list[int],
    ends: list[int],
    *,
    count: int,
    start: int,
    end: int,
) -> tuple[
    bool,
    int,
]:
    """Determine if the event is schedulable in the provided schedule.

    If so, say where. If not, say where.
    """

    if count == 0:
        pos = 0
    elif ends[-1] <= start:
        pos = count
    elif starts[0] >= end:
        pos = 0
    else:
        after_index = closest_left_neighbor(ends, start, count=count)
        pos = after_index + 1
        if start < ends[after_index]:
            return False, after_index
        elif pos < count and end > starts[pos]:
            return False, pos

    return True, pos


class MyCalendarTwo:
    starts_p: list[int]
    starts_q: list[int]
    ends_p: list[int]
    ends_q: list[int]

    def __init__(self):
        self.count_p = 0
        self.count_q = 0

        self.starts_p = list()
        self.starts_q = list()

        self.ends_p = list()
        self.ends_q = list()

    def book(self, start: int, end: int) -> bool:

        # NOTE: Check $Q$ schedulable.
        is_schedulable_q, left_index_q = is_schedulable(
            self.starts_q,
            self.ends_q,
            count=self.count_q,
            start=start,
            end=end,
        )
        if not is_schedulable_q:
            return False

        # NOTE: Check $P$ schedulable.
        is_schedulable_p, p_left_index = is_schedulable(
            self.starts_p,
            self.ends_p,
            count=self.count_p,
            start=start,
            end=end,
        )
        if is_schedulable_p:
            print(p_left_index)
            self.count_p += 1
            self.starts_p.insert(p_left_index, start)
            self.ends_p.insert(p_left_index, end)
            return True

        # NOTE: If not $P$ schedulable, find intersecting.

        # nearest end before start, closest start after end
        index_intersects_before = closest_left_neighbor(
            self.ends_p, start, count=self.count_p
        )
        index_intersects_after = closest_left_neighbor(
            self.starts_p, end, count=self.count_p
        )

        start_intersects_before = self.starts_p[index_intersects_before]
        end_intersects_after = self.ends_p[index_intersects_after]

        contains_start = min(start_intersects_before, start)
        contains_end = max(end_intersects_after, end)

        if index_intersects_before == index_intersects_after:
            index_intersects_after += 1

        contained_start = self.starts_p[index_intersects_before:index_intersects_after]
        contained_end = self.ends_p[index_intersects_before:index_intersects_after]

        print(
            {
                "start": start,
                "end": end,
                "index_intersects_before": index_intersects_before,
                "index_intersects_after": index_intersects_after,
                "start_intersects_before": start_intersects_before,
                "end_intersects_after": end_intersects_after,
                "contains_start": contains_start,
                "contains_end": contains_end,
                "contained_start": contained_start,
                "contained_end": contained_end,
            }
        )

        self.starts_p = [
            *self.starts_p[:index_intersects_before],
            contains_start,
            *self.starts_p[index_intersects_after:],
        ]
        self.ends_p = [
            *self.ends_p[:index_intersects_before],
            contains_end,
            *self.ends_p[index_intersects_after:],
        ]

        self.starts_q = [
            *self.starts_q[: left_index_q + 1],
            *contained_start,
            *self.starts_q[left_index_q:],
        ]
        self.ends_q = [
            *self.ends_q[: left_index_q + 1],
            *contained_end,
            *self.ends_q[left_index_q:],
        ]

        return True

    # def book(self, start: int, end: int) -> bool:
    #
    #     # NOTE: Try to book in $P$ and $Q$.
    #     p_booked, p_after = book(
    #         self.starts_p, self.ends_p, count=self.count_p, start=start, end=end
    #     )
    #     if p_booked:
    #         print(f"Booked `{(start, end)}` in `p`.")
    #         self.count_p += 1
    #         return True
    #
    #     q_booked, q_after = book(
    #         self.starts_q, self.ends_q, count=self.count_q, start=start, end=end
    #     )
    #     if q_booked:
    #         print(f"Booked `{(start, end)}` in `q`.")
    #         self.count_q += 1
    #         return True
    #
    #     # NOTE: See if collisions in $P$ and $Q$ intersect, if not, split
    #     #       and book chunks.
    #     pp = (self.starts_p[p_after], self.ends_p[p_after])
    #     qq = (self.starts_q[q_after], self.ends_q[q_after])
    #
    #     if pp[0] < qq[0]:
    #         left, right = pp, qq
    #         p_start, p_end = right[0], end
    #         q_start, q_end = start, right[0]
    #     else:
    #         left, right = qq, pp
    #         p_start, p_end = start, right[0]
    #         q_start, q_end = right[0], end
    #
    #     print(f"`{p_after = }`", f"`{q_after = }`")
    #     print(f"`{left = }`, `{right = }`.")
    #
    #     # If the end of the left event exceeds the right event, unschedulable.
    #     if left[1] > right[0]:
    #         print(f"Could not book `{(start, end)}`.")
    #         return False
    #
    #     print(f"Split `{(start, end)}` at `{right[0]}`.")
    #     p_booked, p_after = book(
    #         self.starts_p, self.ends_p, count=self.count_p, start=p_start, end=p_end
    #     )
    #     if not p_booked:
    #         print(f"Failed to book `{(start, right[0])}` in p")
    #         return False
    #
    #     q_booked, _ = book(
    #         self.starts_q, self.ends_q, count=self.count_q, start=q_start, end=q_end
    #     )
    #     if not q_booked:
    #         print(f"Failed to book `{(right[0], end)}` in q")
    #         self.starts_p.pop(p_after)
    #         self.ends_p.pop(p_after)
    #         return False
    #
    #     self.count_p += 1
    #     self.count_q += 1
    #
    #     return True


@pytest.fixture
def solution():
    return MyCalendarTwo()


with open(pathlib.Path(__file__).resolve().parent / "cases.yaml") as file:
    cases = list(item.values() for item in yaml.safe_load(file))


@pytest.mark.skip
@pytest.mark.parametrize("question, answer", cases)
def test_solution(
    solution: MyCalendarTwo,
    question: list[tuple[int, int]],
    answer: list[bool],
):

    for (start, end), aa in zip(question, answer):
        print("===========================================")
        aa_computed = solution.book(start, end)
        print(list(zip(solution.starts_p, solution.ends_p)))
        print(list(zip(solution.starts_q, solution.ends_q)))

        assert solution.starts_p == sorted(solution.starts_p), "``starts_p`` not sorted"
        assert solution.ends_p == sorted(solution.ends_p), "``ends_p`` not sorted"
        assert solution.starts_q == sorted(solution.starts_q), "``starts_q`` not sorted"
        assert solution.ends_q == sorted(solution.ends_q), "``ends_p`` not sorted"

        assert all(
            solution.starts_p[k] <= solution.ends_p[k] for k in range(solution.count_p)
        )
        assert all(
            solution.starts_q[k] <= solution.ends_q[k] for k in range(solution.count_q)
        )

        assert aa_computed == aa, f"Expected `{aa}`, got `{aa_computed}`."


# Your MyCalendarTwo object will be instantiated and called as such:
# obj = MyCalendarTwo()
# param_1 = obj.book(star
