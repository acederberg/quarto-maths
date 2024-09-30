import pathlib
from typing import Literal

import pytest
import yaml


# start snippet not_lazy
class CustomStackInitial:

    top_max: int
    top: int
    data: list[int]

    def __init__(self, maxSize: int):

        self.top_max = maxSize - 1
        self.top = -1
        self.data = [-1 for _ in range(maxSize)]

    def push(self, x: int) -> None:
        if self.top == self.top_max:
            return

        self.top += 1
        self.data[self.top] = x

    def pop(self) -> int:
        if self.top < 0:
            return -1

        x = self.data[self.top]
        self.data[self.top] = -1
        self.top -= 1
        return x

    def increment(self, k: int, val: int) -> None:

        # NOTE: Use the minimum since if ``k`` exceeds ``top_max`` all elements
        #       should be incremented. Should do nothing when ``k=0``.
        for j in range(min(k, self.top_max + 1)):
            self.data[j] += val

        return
        # end snippet not_lazy


# start snippet solution
class CustomStack:

    top_max: int
    top: int
    data: list[int]

    def __init__(self, maxSize: int):

        self.top_max = maxSize - 1
        self.top = -1
        self.data = [-1 for _ in range(maxSize)]
        self.increments = [0 for _ in range(maxSize)]

    def push(self, x: int) -> None:
        if self.top == self.top_max:
            return

        self.top += 1
        self.data[self.top] = x

    def pop(self) -> int:
        if self.top < 0:
            return -1

        x = self.data[self.top]
        y = self.increments[self.top]

        self.data[self.top] = -1
        self.increments[self.top] = 0
        self.top -= 1

        if self.top > -1:
            self.increments[self.top] += y

        return x + y

    def increment(self, k: int, val: int) -> None:

        if self.top < 0:
            return

        index = min(k - 1, self.top)
        self.increments[index] += val

        return
        # end snippet solution


CASES = pathlib.Path(__file__).parent.resolve() / "cases.yaml"
with open(CASES, "r") as file:
    cases = tuple(item.values() for item in yaml.safe_load(file))


def test_customstack_basic():
    stack = CustomStackInitial(3)

    assert stack.top == -1
    assert all(-1 == item for item in stack.data)
    assert stack.top_max == 2

    stack.push(1)
    stack.push(2)

    assert stack.top == 1
    assert stack.data == [1, 2, -1]

    assert 2 == stack.pop()
    assert stack.top == 0
    assert stack.data == [1, -1, -1]

    stack.push(2)
    stack.push(3)

    assert stack.data == [1, 2, 3]
    assert stack.top == 2

    stack.push(5)
    assert stack.data == [1, 2, 3]
    assert stack.top == 2

    stack.increment(5, 100)
    assert stack.data == [101, 102, 103]

    stack.increment(3, 100)
    assert stack.data == [201, 202, 203]

    stack.increment(1, 100)
    assert stack.data == [301, 202, 203]

    stack.increment(0, 666)
    assert stack.data == [301, 202, 203]


def test_customstack_basic_2():
    stack = CustomStack(3)

    assert stack.top == -1 and stack.top_max == 2
    assert all(-1 == item for item in stack.data)
    assert all(0 == item for item in stack.increments)

    stack.push(1)
    stack.push(2)
    assert stack.data == [1, 2, -1]
    assert stack.increments == [0, 0, 0]

    stack.push(3)
    assert stack.data == [1, 2, 3]
    assert stack.top == 2

    stack.push(5)
    assert stack.data == [1, 2, 3]
    assert stack.top == 2

    stack.increment(3, 5)
    assert stack.data == [1, 2, 3]
    assert stack.increments == [0, 0, 5]

    assert stack.pop() == 8
    assert stack.data == [1, 2, -1]
    assert stack.increments == [0, 5, 0]

    assert stack.pop() == 7
    assert stack.data == [1, -1, -1]
    assert stack.increments == [5, 0, 0]

    stack.push(3)
    assert stack.data == [1, 3, -1]
    assert stack.increments == [5, 0, 0]

    assert stack.pop() == 3
    assert stack.pop() == 6
    assert stack.pop() == -1

    stack.push(55)
    assert stack.data == [55, -1, -1]
    assert stack.increments == [0, 0, 0]

    stack.push(66)
    stack.push(77)
    assert stack.data == [55, 66, 77]

    stack.increment(5, 100)
    assert stack.increments == [0, 0, 100]

    stack.increment(2, 100)
    assert stack.increments == [0, 100, 100]

    assert stack.pop() == 177
    assert stack.increments == [0, 200, 0]

    assert stack.pop() == 266
    assert stack.increments == [200, 0, 0]

    assert stack.pop() == 255
    assert stack.increments == [0, 0, 0]


@pytest.mark.parametrize("size, methods, args, result", cases)
def test_solution(
    size: int,
    methods: list[Literal["push", "pop", "increment"]],
    args: list[tuple[int] | tuple[int, int] | tuple],
    result: list[None | int],
):
    stack = CustomStack(size)
    result_computed = []

    for method_name, method_args in zip(methods, args):

        if (method := getattr(stack, method_name, None)) is None:
            raise ValueError(f"No such method `{method_name}` of `Stack`.")

        result_computed.append(method(*method_args))

        print("-------------------------------------------------")
        print(method_name, method_args)
        print(list(zip(stack.increments, stack.data)))
        print(stack.top)

    print(result)
    print(result_computed)
    assert result == result_computed
