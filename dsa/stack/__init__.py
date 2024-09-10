import secrets
from collections.abc import Iterable
from typing import Generator, Generic, Sequence, TypeVar

from typing_extensions import Self

T_Stack = TypeVar("T_Stack")


class Stack(Generic[T_Stack]):

    identity: str
    memory: list[T_Stack]
    index: int

    def __init__(self, identity: str | None = None):
        # NOTE: In ``C``, this is just an array for which some resizing may
        #       have to occur.
        self.identity = identity if identity is not None else secrets.token_hex(8)
        self.memory = list()
        self.index = -1

    @classmethod
    def fromIterable(cls, items: Iterable[T_Stack], **kwargs) -> Self:
        self = cls(**kwargs)
        for item in items:
            self.push(item)

        return self

    def push(self, item: T_Stack) -> None:
        self.index += 1
        self.memory.append(item)  # Yes, append is bad.

    def pop(self) -> T_Stack:
        if self.index == -1:
            raise ValueError(f"Stack `{self.identity}` is empty.")

        top = self.memory.pop(self.index)
        self.index -= 1
        return top

    @property
    def top(self) -> T_Stack:
        if self.index == -1:
            raise ValueError(f"Stack `{self.identity}` is empty.")

        return self.memory[self.index]


def hanoi_turn(s: Stack[int], t: Stack[int]):

    if s.index == -1:
        s.push(t.pop())
        return
    elif t.index == -1:
        t.push(s.pop())
        return

    bigger, smaller = (s, t) if s.top > t.top else (t, s)
    bigger.push(smaller.pop())


def hanoi(a: Stack[int], b: Stack[int], c: Stack[int]) -> Generator[None, None, None]:

    n = len(a.memory)
    pairs = (a, b), (c, a), (b, c)
    if not all(p > q for p, q in zip(a.memory[:-1], a.memory[1:])):
        raise ValueError("`a` must be sorted from greatest to least value.")

    turn = 0
    while len(c.memory) != n and len(b.memory) != n:

        yield
        s, t = pairs[turn % 3]
        hanoi_turn(s, t)
        turn += 1


def main():
    size = 25

    a = Stack[int](identity="a")
    for k in range(size):
        a.push(size - k)

    turns = 0
    n = 0
    for _ in hanoi(a, b := Stack[int](identity="b"), c := Stack[int](identity="c")):

        if not n:
            _n = input("Enter the number of turns to execute: ")
            print()
            n = 1 if not _n.isnumeric() else int(_n)
            print(n)

        elif n == 1:
            print(a.identity, a.memory)
            print(b.identity, b.memory)
            print(c.identity, c.memory)
            print()

        turns += 1
        n -= 1

    print(f"Completed after `{turns}` turns!")
    print()
    print(a.identity, a.memory)
    print(b.identity, b.memory)
    print(c.identity, c.memory)


if __name__ == "__main__":
    main()
