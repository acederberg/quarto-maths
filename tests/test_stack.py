import random

import pytest

from dsa.stack import Stack, hanoi


def test_basic():
    s = Stack()
    assert s.index == -1

    with pytest.raises(ValueError) as err:
        s.top

    assert str(err.value).endswith(" is empty.")

    for k in range(100):
        s.push(top := random.randint(0, 100))
        assert s.index == k
        assert s.top == top

    for k in range(100):
        assert s.index == 100 - 1 - k

        top = s.top
        top_pop = s.pop()

        assert top == top_pop


@pytest.mark.parametrize("size", list(range(4, 10)))
def test_hanoi(size: int):
    a, b, c = (
        Stack[int].fromIterable(map(lambda item: size - item, range(size))),
        Stack[int](),
        Stack[int](),
    )
    turns = 0
    for _ in hanoi(a, b, c):
        assert all(
            s > t
            for stack in (a, b, c)
            if stack.index > 0
            for s, t in zip(stack.memory[:-1], stack.memory[1:])
        )
        turns += 1

    assert turns == (2**size) - 1
    assert a.index == -1
    if not (size % 2):
        assert c.index == size - 1
        assert b.index == -1
    else:
        assert b.index == size - 1
        assert c.index == -1
