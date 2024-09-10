from dsa.queue import Queue


def test_basic():
    q = Queue[int]()
    assert q.head is None and q.tail is None

    q.enqueue(1)
    assert q.head is not None and q.tail is not None
    assert q.head.value == 1 and q.tail.value == 1

    q.enqueue(2)
    assert q.head is not None and q.tail is not None
    assert q.head.value == 1 and q.tail.value == 2

    q.enqueue(3)
    assert q.head is not None and q.tail is not None
    assert q.head.value == 1 and q.tail.value == 3

    # NOTE: Non-destructive
    assert list(q.values()) == [1, 2, 3]

    h = q.head  # save to ensure delinking in underlying linked list.
    v = q.dequeue()
    assert h.before is None and h.after is None
    assert q.head is not None and q.tail is not None
    assert v == 1 and q.head.value == 2 and q.tail.value == 3

    h = q.head
    v = q.dequeue()
    assert h.before is None and h.after is None
    assert q.head is not None and q.tail is not None
    assert v == 2 and q.head.value == 3 and q.tail.value == 3

    h = q.head
    v = q.dequeue()
    assert h.before is None and h.after is None
    assert v == 3 and q.head is None and q.tail is None

    v = q.dequeue()
    assert v is None and q.head is None and q.tail is None
