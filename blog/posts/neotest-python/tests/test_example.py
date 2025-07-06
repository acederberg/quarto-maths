"""
Verify that neotest and nvim-dap works with python.

Pass and fail icons should show up in the left hand side,
add failed assertions should have diagnostics.

```

"""

import pytest

import example_neotest as example


def test_sum():

    assert 1 + 1 == 2
    assert 2 + 2 != 3
    assert 5 + 5 == 10


def test_comprehension():

    compr = [x**2 for x in range(1, 10, 2)]
    assert len(compr) == 5
    assert compr[0] == 1 and compr[-1] == 9**2  # This should fail, it is 81


class TestClass:

    def test_string(self):

        string = "This is a statement."
        assert "This" in string
        assert string.split() == ["This", "is", "a", "statement."]


class TestExample:
    """
    This test should be rerun when `example.py` is updated.
    """

    @pytest.mark.parametrize("data", ["this", "is", "a", "test"])
    def test_some_fn(self, data: str):

        assert example.some_fn("It works!") == 42
        assert example.some_fn(data) == 0
