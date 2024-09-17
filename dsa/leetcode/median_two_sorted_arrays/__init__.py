import pytest


# start snippet solution_initial
class Solution:

    # NOTE: Input arrays should already be sorted.
    def findMedianSortedArrays(
        self,
        nums1: list[int],
        nums2: list[int],
    ) -> float:

        n1, n2 = len(nums1), len(nums2)
        if n1 + n2 == 1:
            if n1 != 0:
                return nums1[0]
            else:
                return nums2[0]

        start_1, start_2 = 0, 0
        stop_1, stop_2 = n1 - 1, n2 - 1
        left, right = None, None

        while True:
            # If both, decide which one to decrement/increment
            if start_1 <= stop_1 and start_2 <= stop_2:
                a, b = nums1[start_1], nums2[start_2]
                if a <= b:
                    left = a
                    start_1 += 1
                else:
                    left = b
                    start_2 += 1

                a, b = nums1[stop_1], nums2[stop_2]
                if a >= b:
                    right = a
                    stop_1 -= 1
                else:
                    right = b
                    stop_2 -= 1
            elif start_1 < stop_1:
                left = nums1[start_1]
                right = nums1[stop_1]

                stop_1 -= 1
                start_1 += 1
            elif start_2 < stop_2:
                left = nums2[start_2]
                right = nums2[stop_2]

                stop_2 -= 1
                start_2 += 1
            elif stop_1 == start_1:
                left = right = nums1[stop_1]
                break
            elif stop_2 == start_2:
                left = right = nums2[stop_2]
                break
            else:
                break

        return (left + right) / 2


# end snippet solution_initial


# start snippet solution_2
class Solution2:

    def findMedianSortedArrays(
        self,
        nums1: list[int],
        nums2: list[int],
    ) -> float:

        n1, n2 = len(nums1), len(nums2)
        start_1, start_2 = 0, 0
        stop_1, stop_2 = n1 - 1, n2 - 1
        left, right = None, None

        while True:
            # If both, decide which one to decrement/increment
            if start_1 <= stop_1 and start_2 <= stop_2:
                a, b = nums1[start_1], nums2[start_2]
                if a <= b:
                    left = a
                    start_1 += 1
                else:
                    left = b
                    start_2 += 1

                a, b = nums1[stop_1], nums2[stop_2]
                if a >= b:
                    right = a
                    stop_1 -= 1
                else:
                    right = b
                    stop_2 -= 1

            # If one remains, find its median
            elif start_1 <= stop_1:
                left = nums1[start_1]
                right = nums1[stop_1]

                stop_1 -= 1
                start_1 += 1
            elif start_2 <= stop_2:
                left = nums2[start_2]
                right = nums2[stop_2]

                stop_2 -= 1
                start_2 += 1
            else:
                break

        return (left + right) / 2


# end snippet solution_2


@pytest.fixture
def solution():
    return Solution()


# 1,2,3,
# 4,5,6,
# 7,8,9,
# 10,11, 12,
# 13,14,15,
# 16,17


@pytest.mark.parametrize(
    "nums1, nums2, answer",
    (
        ([3], [-2, -1], -1),
        ([1], [], 1),
        ([1, 2, 3], [], 2),
        ([1, 3], [2], 2.0),
        ([1, 2], [3, 4], 2.5),
        ([5, 6, 7, 8], [4, 9], 6.5),
        ([1, 2, 5, 6], [3, 4], 3.5),
        ([1, 2, 3, 7, 8, 9], [4, 5, 6], 5.0),
        ([2, 2, 4, 4], [2, 2, 2, 4, 4], 2.0),
        ([1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17], 9.0),
    ),
)
def test_solution(
    solution: Solution,
    nums1: list[int],
    nums2: list[int],
    answer: float,
):
    assert solution.findMedianSortedArrays(nums1, nums2) == answer
