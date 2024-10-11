import pytest


# start snippet monotonic_stack_push
def push(stack: list[int], value: int, *, _top: int | None = None) -> int:

    top = _top or (len(stack) - 1)
    while stack and stack[top] > value:
        stack.pop()
        top -= 1

    stack.append(value)

    return top

    # end snippet monotonic_stack_push


class SolutionFailed:
    def maxWidthRamp(self, nums: list[int]) -> int:

        pairs = sorted(enumerate(nums), key=lambda pair: pair[1])
        left = right = pairs[0][0]

        for index, _ in pairs:
            if index < left and nums[index] <= nums[right]:
                left = index
            elif right < index and nums[left] <= nums[index]:
                right = index

        return right - left


# start snippet solution
class Solution:
    def maxWidthRamp(self, nums: list[int]) -> int:

        n = len(nums)
        stack: list[int] = []

        for index in range(n):
            num = nums[index]
            if not stack or nums[stack[-1]] > num:
                stack.append(index)

        max_width = 0
        for k in range(n - 1, -1, -1):
            while stack and nums[stack[-1]] <= nums[k]:
                max_width = max(max_width, k - stack.pop())

        return max_width
        # end snippet solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, answer",
    (
        ([6, 0, 8, 2, 1, 5], 4),
        ([9, 8, 1, 0, 1, 9, 4, 0, 4, 1], 7),
        ([2, 1, 3], 2),
        ([2, 2, 1], 1),
        ([2, 4, 1, 3], 3),
    ),
)
def test_solution(solution: Solution, question: list[int], answer: int):

    answer_computed = solution.maxWidthRamp(question)
    assert answer_computed == answer
