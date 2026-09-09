"""Vector clocks — the causal-ordering token on every kernel record.

Wall-clock time is recorded alongside for humans but is never consulted for
ordering. See docs/clock-skew.md for why.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class VectorClock:
    # Sorted tuple of (agent_id, count) so the value is hashable and canonical.
    counts: tuple[tuple[str, int], ...] = ()

    @staticmethod
    def zero() -> "VectorClock":
        return VectorClock(())

    @staticmethod
    def of(mapping: Mapping[str, int]) -> "VectorClock":
        return VectorClock(tuple(sorted((k, int(v)) for k, v in mapping.items() if v > 0)))

    def as_dict(self) -> dict[str, int]:
        return dict(self.counts)

    def to_canonical(self) -> dict[str, int]:
        return self.as_dict()

    def get(self, agent_id: str) -> int:
        return self.as_dict().get(agent_id, 0)

    def tick(self, agent_id: str) -> "VectorClock":
        d = self.as_dict()
        d[agent_id] = d.get(agent_id, 0) + 1
        return VectorClock.of(d)

    def merge(self, other: "VectorClock") -> "VectorClock":
        d = self.as_dict()
        for k, v in other.counts:
            d[k] = max(d.get(k, 0), v)
        return VectorClock.of(d)

    def __le__(self, other: "VectorClock") -> bool:
        od = other.as_dict()
        return all(od.get(k, 0) >= v for k, v in self.counts)

    def happens_before(self, other: "VectorClock") -> bool:
        return self <= other and self != other

    def concurrent(self, other: "VectorClock") -> bool:
        return not (self <= other) and not (other <= self)
