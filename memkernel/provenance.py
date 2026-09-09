"""Belief provenance: did an agent know memory M when it produced action R?

Two answers are offered. `knew_by_wall_clock` exists ONLY to demonstrate that
it is wrong under clock skew (docs/clock-skew.md, tests/test_clock_skew.py).
The kernel uses `knew_by_causal_order` everywhere.
"""
from __future__ import annotations

from .records import MemoryObject, Record


def knew_by_wall_clock(memory: MemoryObject, action: Record) -> bool:
    """WRONG under skew. Do not use outside the demonstration."""
    return action.wall_clock >= memory.wall_clock


def knew_by_causal_order(memory: MemoryObject, action: Record) -> bool:
    """True iff the memory's creation is in the causal past of the action."""
    return memory.vclock <= action.vclock
