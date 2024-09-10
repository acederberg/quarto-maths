from typing import Generic, Iterator, TypeVar

from typing_extensions import Self

T_Queue = TypeVar("T_Queue")


class QueueNode(Generic[T_Queue]):
    """Doubly linked list for Queue."""

    value: T_Queue
    before: Self | None
    after: Self | None

    def __init__(
        self,
        value: T_Queue,
        before: Self | None = None,
        after: Self | None = None,
    ):
        self.value = value
        self.before = before
        self.after = after


class Queue(Generic[T_Queue]):
    """Obviously a list could be used as the underlying structure, however
    doing so would not be in the spirit of the problem."""

    head: QueueNode[T_Queue] | None
    tail: QueueNode[T_Queue] | None

    def __init__(self):
        self.head = None
        self.tail = None

    def __iter__(self) -> Iterator[T_Queue]:
        """Destructive iteration."""
        while (out := self.dequeue()) is not None:
            yield out

    def __bool__(self) -> bool:
        """Is the queue empty?"""
        return self.head is not None or self.tail is not None

    def enqueue(self, item: T_Queue) -> None:
        """Add a node to the end of the underlying linked list and set
        :attr:`tail` to the next element."""

        tail_prev = self.tail
        tail = QueueNode(item, after=tail_prev)
        self.tail = tail

        if tail_prev is not None:
            tail_prev.before = tail

        if self.head is None:
            self.head = self.tail

    def dequeue(self) -> T_Queue | None:
        if (head_prev := self.head) is None:
            return None

        if head_prev == self.tail:
            self.tail = None

        self.head = head_prev.before

        # Unlink.
        if head_prev.before is not None:
            head_prev.before.after = None
            head_prev.before = None
            head_prev.after = None

        return head_prev.value

    def values(self) -> Iterator[T_Queue]:
        head = self.head
        while head is not None:
            yield head.value
            if (head := head.before) is None:
                break
