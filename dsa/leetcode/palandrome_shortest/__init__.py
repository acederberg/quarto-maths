import pytest


# start snippit solution_initial
class SolutionInitial:
    def searchPalindrome(
        self,
        s: str,
        *,
        index_final: int,
        index: int,
        even: bool = False,
    ):

        stop, start = index, index
        if even:
            if stop == index_final:
                return start, start

            stop += 1
            if s[start] != s[stop]:
                return start, start
            delta = min(index_final - 1 - index, index)
        else:
            delta = min(index_final - index, index)

        for _ in range(delta):
            start -= 1
            stop += 1

            if s[start] != s[stop]:
                start += 1
                stop -= 1
                break

        return start, stop

    def shortestPalindrome(self, s: str) -> str:
        n = len(s)
        if n == 1:
            return s

        index_final = n - 1
        best_initial, best_terminal = 0, index_final

        for index in range(n):
            start, stop = self.searchPalindrome(
                s,
                index_final=index_final,
                index=index,
                even=False,
            )
            start_even, stop_even = self.searchPalindrome(
                s,
                index_final=index_final,
                index=index,
                even=True,
            )
            if start_even <= start and stop_even >= stop:
                start = start_even
                stop = stop_even

            # NOTE: If a palindrome is found that is the entire string, return
            #       the entire string. When the stop is is n, a terminal
            #       palindrome is found When the start point is 0, an initial
            #       palindrome is found.
            if start != 0 and stop != n:
                continue
            elif start == 0 and stop == n:
                return s
            elif start == 0 and stop > best_initial:
                best_initial = stop
            elif stop == index_final and start < best_terminal:
                best_terminal = start

        size_terminal = index_final - best_terminal
        size_initial = best_initial

        if size_initial >= size_terminal:
            palindrome = s[: best_initial + 1]
            mantisa = s[best_initial + 1 :]
            return mantisa[::-1] + palindrome + mantisa
        else:
            palindrome = s[best_terminal:]
            mantisa = s[:best_terminal]
            return mantisa + palindrome + mantisa[::-1]

    # stop snippit solution_initial


# start snippet solution
class Solution:
    def isPalindrome(
        self,
        s: str,
        start: int,
        stop: int,
    ):
        t = s[start : stop + 1]
        return t == t[::-1]

    def shortestPalindrome(self, s: str):

        n = len(s)
        if not n:
            return s

        index_final = n - 1
        char_init, char_term = s[0], s[-1]
        best_init, best_term = 0, index_final

        if self.isPalindrome(s, 0, n - 1):
            return s

        for index in range(n - 1):
            char_front = s[index]
            char_back = s[index_final - index]

            if (
                char_front == char_init
                and self.isPalindrome(s, 0, index)
                # and index > best_init
            ):
                best_init = index

            if (
                char_back == char_term
                and self.isPalindrome(s, index_final - index, index_final)
                # and index < best_term
            ):
                best_term = index_final - index

        size_terminal = index_final - best_term
        size_initial = best_init

        if size_initial >= size_terminal:
            palindrome = s[: best_init + 1]
            mantisa = s[best_init + 1 :]
            return mantisa[::-1] + palindrome + mantisa
        else:
            palindrome = s[best_term:]
            mantisa = s[:best_term]
            return mantisa + palindrome + mantisa[::-1]

    # end snippet solution


@pytest.fixture
def solution():
    return Solution()


big = 10**4 * "a"


@pytest.mark.parametrize(
    "question, answer",
    (
        ("a", "a"),
        ("ab", "bab"),
        ("aacecaaa", "aaacecaaa"),
        ("abcd", "dcbabcd"),
        ("aac", "caac"),
        ("kcaaffaack", "kcaaffaack"),
        ("aa", "aa"),
        (
            (big + "c" + big + "d" + big),
            (big + "d" + big + "c" + big + "d" + big),
        ),
    ),
)
def test_solution(solution: Solution, question: str, answer: str):

    answer_computed = solution.shortestPalindrome(question)
    if len(answer) < 1000:
        # print(answer_computed, answer)
        pass
    assert answer_computed == answer


@pytest.mark.parametrize(
    "question, answer",
    (
        ("aa", True),
        ("abbbbba", True),
        ("", True),
        (10**6 * "a", True),
    ),
)
def test_is_palindrome(solution: Solution, question: str, answer: bool):

    n = len(question)
    assert solution.isPalindrome(question, 0, n) == answer
