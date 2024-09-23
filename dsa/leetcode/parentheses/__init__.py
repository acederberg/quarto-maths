from typing import Iterator

import pytest


# start snippet solution_initial
class SolutionInitial:
    def conquer(self, pieces: list[tuple[str, str]], answers: set[str]):
        n = len(pieces)
        if n == 1:
            answers.add(pieces[0][0])
            return
        if n == 2:
            head, next = pieces[0], pieces[1]
            exp = head[0] + head[1] + next[0]
            answers.add(exp)
            return

        for k in range(n - 1):

            head = pieces[k]
            next = pieces[k + 1]
            new = ("(" + head[0] + head[1] + next[0] + ")", next[1])

            self.conquer([*pieces[0:k], new, *pieces[k + 2 :]], answers)

    def parse(self, expression: str) -> list[tuple[str, str]]:
        pieces = []

        current = ""
        for char in expression:

            if char.isnumeric():
                current += char
            else:
                pieces.append((current, char))
                current = ""

        pieces.append((current, ""))
        return pieces

    def diffWaysToCompute(self, expression: str) -> list[int]:
        pieces = self.parse(expression)
        self.conquer(pieces, answers := set())
        return list(eval(thing) for thing in answers)
        # end snippet solution_initial


# start snippet solution_initial
# NOTE: Eval and callstack are problems.
class Solution:
    def conquer(self, *pieces: tuple[str, str], answers: set[str]):
        n = len(pieces)
        if n == 1:
            yield eval(pieces[0][0])
            return
        if n == 2:
            head, next = pieces[0], pieces[1]
            exp = head[0] + head[1] + next[0]
            if exp in answers:
                return

            answers.add(exp)
            yield eval(exp)
            return

        for k in range(n - 1):

            new = (
                "(" + pieces[k][0] + pieces[k][1] + pieces[k + 1][0] + ")",
                pieces[k + 1][1],
            )

            yield from self.conquer(
                *pieces[0:k], new, *pieces[k + 2 :], answers=answers
            )

    def parse(self, expression: str) -> Iterator[tuple[str, str]]:

        current = ""
        for char in expression:
            if char.isnumeric():
                current += char
            else:
                yield (current, char)
                current = ""

        yield (current, "")

    def diffWaysToCompute(self, expression: str) -> list[int]:

        answers = set()
        return list(self.conquer(*self.parse(expression), answers=answers))
        # end snippet solution_initial


@pytest.fixture
def solution():
    return Solution()


@pytest.mark.parametrize(
    "expression, answer",
    (
        (("2+5"), [7]),
        ("2-1-1", [0, 2]),
        # ("2+3*5-4", [21, 13, 11, 6, 5]),
        ("2*3-4*5", [-34, -14, -10, -10, 10]),
        ("0", [0]),
    ),
)
def test_solution(solution: Solution, expression: str, answer: list[int]):

    answer = sorted(answer)
    answer_computed = sorted(solution.diffWaysToCompute(expression))
    print(answer, answer_computed)
    assert answer == answer_computed
