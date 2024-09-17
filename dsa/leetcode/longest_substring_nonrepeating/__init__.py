import pytest


# start snippet solution_initial
class SolutionInitial:
    def longestSubstring(self, s: str) -> tuple[str, int]:

        seen: dict[str, int] = dict()

        start = 0
        best_start, best_stop = 0, 0
        best_size = -1

        for k, char in enumerate(s):

            if (char_last_seen := seen.get(char)) is not None:
                start = max(start, char_last_seen + 1)

            if (diff := k - start) > best_size:
                # print("-->", "new best")
                best_start, best_stop = start, k
                best_size = diff

            seen[char] = k
            # print(s)
            # print(((start) * " ") + ((diff + 1) * "^"))

        if best_size == -1:
            return "", 0

        return s[best_start : best_stop + 1], 1 + best_stop - best_start

    def lengthOfLongestSubstring(self, s: str) -> int:
        _, best_size = self.longestSubstring(s)
        return best_size
        # end snippet solution_initial


# start snippet solution
class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:

        seen: dict[str, int] = dict()

        start = 0
        best_size = -1

        for k, char in enumerate(s):
            if char in seen:
                start = max(start, seen[char] + 1)
                seen.pop(char)

            if (diff := k - start) > best_size:
                best_size = diff

            seen[char] = k

        return best_size + 1
        # end snippet solution


@pytest.fixture
def solution_initial():
    return SolutionInitial()


@pytest.fixture
def solution():
    return Solution()


cases = (
    ("nnnnnn", "n"),
    ("abcabcbb", "abc"),
    ("pwwkew", "wke"),
    ("dvdf", "vdf"),
    ("peeeeppeepoopooo", "epo"),
    ("", ""),
)


@pytest.mark.parametrize("question, answer", cases)
def test_solution_init(solution_initial: SolutionInitial, question: str, answer: str):
    got, got_size = solution_initial.longestSubstring(question)
    print(got, answer)
    assert got == answer
    assert len(got) == got_size


@pytest.mark.parametrize("question, answer", cases)
def test_solution(solution: Solution, question: str, answer: str):
    got_size = solution.lengthOfLongestSubstring(question)
    print(got_size, len(answer))
    assert len(answer) == got_size
