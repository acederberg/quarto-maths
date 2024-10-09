import pytest


# start snippet solution
class Solution:
    def minAddToMakeValid(self, s: str) -> int:
        n_open_unclosed = 0
        n_closed_unopened = 0

        for char in s:
            if char == "(":
                n_open_unclosed += 1
            else:
                # NOTE: There is an opening bracket to close this closing 
                #       bracket in the first case.
                if n_open_unclosed > 0:
                    n_open_unclosed -= 1
                else:
                    n_closed_unopened+= 1

        return n_open_unclosed + n_closed_unopened
        # end snippet solution



@pytest.fixture
def solution(): return Solution()


@pytest.mark.parametrize(
    "question, answer",
    (
        ("())", 1),
        ("(((", 3),
        ("()(()((", 3),
        ("()))((", 4),
    ),
)
def test_solution(solution: Solution, question: str, answer: int):

    answer_computed = solution.minAddToMakeValid(question)
    assert answer_computed == answer
