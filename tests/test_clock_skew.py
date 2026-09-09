"""Mechanism assertion: under clock skew, wall-clock ordering gives a provably
wrong answer about what an agent knew; causal ordering gives the right one.

Scenario (docs/clock-skew.md):
  1. Agent A promotes memory M at its wall time 1000.
  2. Agent B's clock runs 120 s slow. B reads M (merging A's clock), then
     produces action R, stamped wall 885 — "before" M.
  3. Agent C's clock runs 120 s fast. C never reads M and produces R' stamped
     wall 1125 — "after" M.
Wall clock says: B did not know M (wrong), C knew M (wrong).
Causal order says: B knew M (right), C did not (right).
"""
from memkernel import MemoryObject, Record, VectorClock
from memkernel.provenance import knew_by_causal_order, knew_by_wall_clock

A_CLOCK = VectorClock.of({"A": 1})
M = MemoryObject(
    content="pattern", provenance=("r",), input_hashes=("i",), labels=("bad",),
    proposed_by=("A",), approved_by="gate", vclock=A_CLOCK, wall_clock=1000.0,
)

# B reads M: merge(A:1) then tick(B) => {A:1, B:1}. Skewed wall clock: 1005 - 120.
R_B = Record(
    id="R_B", content="uses pattern", input_hash="i2", agent_id="B",
    vclock=M.vclock.merge(VectorClock.zero()).tick("B"), wall_clock=885.0, label="bad",
)
# C never reads M: {C:1}. Fast wall clock: 1005 + 120.
R_C = Record(
    id="R_C", content="unrelated", input_hash="i3", agent_id="C",
    vclock=VectorClock.zero().tick("C"), wall_clock=1125.0, label="bad",
)


def test_wall_clock_is_wrong_in_both_directions():
    assert knew_by_wall_clock(M, R_B) is False     # false negative
    assert knew_by_wall_clock(M, R_C) is True      # false positive


def test_causal_order_is_right_in_both_directions():
    assert knew_by_causal_order(M, R_B) is True
    assert knew_by_causal_order(M, R_C) is False
    assert M.vclock.happens_before(R_B.vclock)
    assert M.vclock.concurrent(R_C.vclock)


def test_demonstration_is_reproducible():
    """The demonstration depends on nothing but the fixed values above."""
    for _ in range(3):
        assert (knew_by_wall_clock(M, R_B), knew_by_wall_clock(M, R_C)) == (False, True)
        assert (knew_by_causal_order(M, R_B), knew_by_causal_order(M, R_C)) == (True, False)
