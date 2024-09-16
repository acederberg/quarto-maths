import pytest


# start snippet solution
class Solution:
    def coords(self, m: int, n_rows: int):
        n = n_rows
        N = n - 1
        if N == 0:
            yield from range(m)
            return

        incr = 2 * N
        jj_max = (m // incr) + 1
        yield from (num for jj in range(jj_max) if (num := incr * jj) < m)

        for kk in range(1, n - 1):

            for jj in range(jj_max):

                aa = (incr * jj) + kk
                bb = (incr * (jj + 1)) - kk

                if aa < m:
                    yield aa
                if bb < m:
                    yield bb

        yield from (num for jj in range(jj_max) if (num := (incr * jj) + N) < m)

    def convert(self, s: str, numRows: int) -> str:
        m = len(s)
        nums = self.coords(m, numRows)
        return "".join((s[num] for num in nums))


# end snippet solution


# start snippet solution_better
class SolutionBetter:
    def convert(self, s: str, numRows: int) -> str:
        n = len(s)
        N = numRows - 1
        rows = ["" for _ in range(n)]

        current_row = 0
        incr = -1

        for char in s:
            if current_row == N or current_row == 0:
                incr = -1 * incr

            rows[current_row] += char
            current_row = current_row + incr

        return "".join(rows)


# end snippet solution_better


@pytest.fixture
def solution():
    return SolutionBetter()


@pytest.mark.parametrize(
    "question, numRows, answer",
    (
        # From post
        ("AAAABBCCCCDD", 4, "ACABCDABCDAC"),
        ("PAYPALISHIRING", 3, "PAHNAPLSIIGYIR"),
        ("PAYPALISHIRING", 4, "PINALSIGYAHRPI"),
        # Trivial
        ("A", 5, "A"),
        ("A", 1, "A"),
        ("ABCDE", 4, "ABCED"),
        # a   e   i
        # b d f h j l
        # c   g   k
        ("abcdefghijkl", 3, "aeibdfhjlcgk"),
    ),
)
def test_solution(solution: Solution, question: str, numRows: int, answer: str):

    assert solution.convert(question, numRows) == answer
