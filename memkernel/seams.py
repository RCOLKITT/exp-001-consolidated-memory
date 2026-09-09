"""The three seams between kernel and domain adapter (spec §2).

The kernel imports only these Protocols. A domain adapter provides concrete
classes. Everything the kernel does with domain content goes through here.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .records import MemoryObject, Record


@runtime_checkable
class Oracle(Protocol):
    """Outcome oracle: label(action) -> good | bad | unknown."""

    def label(self, record: Record) -> str: ...


@runtime_checkable
class Similarity(Protocol):
    """sim(candidate, memory) -> [0, 1]. Must be deterministic."""

    def sim(self, a: str, b: str) -> float: ...


@runtime_checkable
class Contradiction(Protocol):
    """Does promoting `candidate_content` contradict an existing promoted memory?

    Returns the ids of contradicted memories (empty = no contradiction).
    """

    def contradicted(self, candidate_content: str, memory: Sequence[MemoryObject]) -> tuple[str, ...]: ...


class NoContradiction:
    def contradicted(self, candidate_content: str, memory: Sequence[MemoryObject]) -> tuple[str, ...]:
        return ()


class PassthroughOracle:
    """Oracle for streams whose records already carry a label (synthetic Phase 1)."""

    def label(self, record: Record) -> str:
        return record.label or "unknown"


class TokenJaccardSimilarity:
    """Deterministic, dependency-free similarity used for Phase 1.

    The code adapter replaces this with embedding cosine (spec §2); the kernel
    never assumes anything beyond the [0, 1] contract.
    """

    def sim(self, a: str, b: str) -> float:
        ta, tb = set(a.split()), set(b.split())
        if not ta and not tb:
            return 1.0
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)
