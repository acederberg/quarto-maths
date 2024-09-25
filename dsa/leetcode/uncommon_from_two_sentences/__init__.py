import pytest


class Solution:
    def uncommonFromSentences(self, s1: str, s2: str) -> list[str]:

        all = s1.split(" ") + s2.split(" ")
        counts: dict[str, int] = dict()

        for word in all:
            counts[word] = counts.get(word, 0) + 1

        return list(word for word, count in counts.items() if count == 1)


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "s1, s2, answer",
    (
        ("this apple is sweet", "this apple is sour", ["sweet", "sour"]),
        ("apple apple", "banana", ["banana"]),
        (
            "what is wrong with you",
            "what is wrong with the world",
            ["you", "the", "world"],
        ),
    ),
)
def test_solution(solution: Solution, s1: str, s2: str, answer: str):

    got = solution.uncommonFromSentences(s1, s2)
    print(got, answer)
    assert sorted(got) == sorted(answer)
