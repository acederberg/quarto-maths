import pathlib
import pytest
import yaml


# start snippet solution_trivial
class Solution:
    def arrayRankTransform(self, arr: list[int]) -> list[int]:
        ranks = {
            item: pos + 1
            for pos, item in enumerate(sorted(set(arr)))
        }

        return [ranks[item] for item in arr]
        # end snippet solution_trivial


@pytest.fixture
def solution(): return Solution()


with open( pathlib.Path(__file__).parent.resolve() / "cases.yaml", "r") as file:
    cases = [item.values() for item in yaml.safe_load(file)]


@pytest.mark.parametrize(
    "question, answer",
    cases
)
def test_solution(solution: Solution, question: list[int], answer: list[int]):
    answer_computed = solution.arrayRankTransform(question) 
    print(answer_computed)
    assert answer_computed == answer
