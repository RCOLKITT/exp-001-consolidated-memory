import dataclasses

from memkernel import Ledger, VectorClock


def test_chain_verifies_and_detects_tamper():
    l = Ledger()
    vc = VectorClock.zero()
    for i in range(5):
        vc = vc.tick("k")
        l.append("e", {"i": i}, vc, 100.0 + i)
    assert l.verify() == (True, None)
    # tamper with payload of entry 2
    e = l._entries[2]
    l._entries[2] = dataclasses.replace(e, payload={"i": 99})
    assert l.verify() == (False, 2)


def test_wall_clock_excluded_from_hash():
    a, b = Ledger(), Ledger()
    vc = VectorClock.zero().tick("k")
    a.append("e", {"x": 1}, vc, 1.0)
    b.append("e", {"x": 1}, vc, 999.0)
    assert a.chain() == b.chain()
