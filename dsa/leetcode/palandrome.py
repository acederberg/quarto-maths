"""Find the biggest palandrome substring within a string.

~~~yaml
url: https://leetcode.com/problems/longest-palindromic-substring/
runtime_quantile: 94%
memory_quantile: 23%
~~~
"""

import pytest


class Solution:
    def doesMatch(self, s: str, n: int, *, start: int, stop: int):

        # NOTE: If beyond string bounds, went t0o far. If not matching, went to
        #       far.
        if stop > n - 1 or start < 0:
            return start + 1, stop - 1
        elif s[start] != s[stop]:
            return start + 1, stop - 1

        start -= 1
        stop += 1

        return self.doesMatch(s, n, start=start, stop=stop)

    def longestPalindrome(self, s: str) -> str:
        pos = 0

        size_best = 0
        best = ""
        n = len(s)
        if n == 1:
            return s

        while pos < n - 1:
            char, next_char = s[pos], s[pos + 1]
            iseven = char == next_char

            start, stop = pos, pos + iseven
            start, stop = self.doesMatch(s, n, start=start, stop=stop)
            size = stop - start

            if size >= size_best:
                size_best = size
                best = s[start : stop + 1]

            if iseven:
                start, stop = self.doesMatch(s, n, start=start, stop=stop - 1)
                size = stop - start

                if size >= size_best:
                    size_best = size
                    best = s[start : stop + 1]

            pos += 1

        return best


@pytest.fixture(scope="session")
def solution():
    return Solution()


@pytest.mark.parametrize(
    "question, answer",
    [
        ("a", "a"),
        ("ccc", "ccc"),
        ("dac", "a"),
        ("daac", "aa"),
        ("aaabbaaa", "aaabbaaa"),
        ("aa", "aa"),
        ("dcaaabbaaacfg", "caaabbaaac"),
        ("1123211011", "1123211"),
        ("1234555504321234", "4321234"),
    ],
)
def test(solution: Solution, question: str, answer: str):

    assert solution.longestPalindrome(question) == answer
