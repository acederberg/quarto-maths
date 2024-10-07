import pytest


HEADS = {"A": "B", "C": "D"}


# start snippet solution
class Solution:
    def getRadius(self, s: str, n: int, index: int):

        radius = 0
        while (
            (index - radius >= 0)
            and (index + 1 + radius < n)
            and s[index - radius] in HEADS
            and HEADS[s[index - radius]] == s[index + radius + 1]
        ):
            radius += 1

        return radius

    def minLength(self, s: str) -> int:

        n = len(s)
        index = 0
        while index < n:
            if (radius := self.getRadius(s, n, index)) > 0:
                s = s[:index + 1 - radius] + s[index + radius + 1:]
                n -= 2 * radius
                index -= radius - 1
            else:
                index += 1

        return n
        # end snippet solution


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "s, index, answer",
    (
        ("ABFCACDB", 0, 1),
        ("ABFCACDB", 4, 0),
        ("ABFCACDB", 5, 2),
        ("CACACABDBDBDB", 5, 6),
    ),
)
def test_get_radius(solution: Solution, s: str, index: int, answer: int):

    answer_computed = solution.getRadius(s, len(s), index)
    assert answer_computed == answer


@pytest.mark.parametrize(
    "s, answer",
    (
        ("ABFCACDB", 2),
        ("ACBBD", 5),
        ("CACACABDBDBDB", 1),
        (
            "CCDAABBDCD", 0),

    )
)
def test_solution(solution: Solution, s: str, answer: int):
    answer_computed = solution.minLength(s) 
    assert answer == answer_computed
