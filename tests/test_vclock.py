from memkernel.vclock import VectorClock


def test_tick_and_merge():
    a = VectorClock.zero().tick("A")
    b = VectorClock.zero().tick("B")
    m = a.merge(b)
    assert m.as_dict() == {"A": 1, "B": 1}
    assert a <= m and b <= m
    assert a.happens_before(m)
    assert a.concurrent(b)


def test_canonical_is_sorted_and_hashable():
    x = VectorClock.of({"b": 2, "a": 1})
    y = VectorClock.of({"a": 1, "b": 2})
    assert x == y and hash(x) == hash(y)
    assert x.counts == (("a", 1), ("b", 2))
