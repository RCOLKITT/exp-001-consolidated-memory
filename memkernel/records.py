"""Kernel record types.

`Record`       — a candidate observation arriving at the kernel (an action the
                 domain produced; e.g. one verifier finding).
`MemoryObject` — an immutable, content-addressed memory. Its id is the digest
                 of every field except wall_clock, so replay from identical
                 inputs yields identical ids and wall-clock drift never
                 changes identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Optional

from .canon import digest
from .vclock import VectorClock

Label = Literal["good", "bad", "unknown"]
LABELS: tuple[str, ...] = ("good", "bad", "unknown")


@dataclass(frozen=True)
class Record:
    id: str
    content: str
    input_hash: str          # hash of the artifact the record came from
    agent_id: str            # proposing agent (for separation of duties)
    vclock: VectorClock
    wall_clock: float        # recorded, never used for ordering
    label: Optional[str] = None  # filled by the outcome oracle at ingest

    def with_label(self, label: str) -> "Record":
        if label not in LABELS:
            raise ValueError(f"bad label {label!r}")
        return replace(self, label=label)

    def to_canonical(self) -> dict:
        # wall_clock deliberately excluded
        return {
            "id": self.id,
            "content": self.content,
            "input_hash": self.input_hash,
            "agent_id": self.agent_id,
            "vclock": self.vclock.to_canonical(),
            "label": self.label,
        }


@dataclass(frozen=True)
class MemoryObject:
    content: str
    provenance: tuple[str, ...]      # source record ids, sorted
    input_hashes: tuple[str, ...]    # distinct artifacts, sorted
    labels: tuple[str, ...]          # labels of the source records, sorted
    proposed_by: tuple[str, ...]     # proposing agents, sorted
    approved_by: str                 # the gate/agent that approved promotion
    vclock: VectorClock              # causal token at creation
    wall_clock: float                # recorded, never used for ordering
    kind: str = "promoted"
    supersedes: Optional[str] = None
    note: str = ""                   # free-text reason for supersession etc.

    def to_canonical(self) -> dict:
        return {
            "content": self.content,
            "provenance": list(self.provenance),
            "input_hashes": list(self.input_hashes),
            "labels": list(self.labels),
            "proposed_by": list(self.proposed_by),
            "approved_by": self.approved_by,
            "vclock": self.vclock.to_canonical(),
            "kind": self.kind,
            "supersedes": self.supersedes,
            "note": self.note,
        }

    @property
    def id(self) -> str:
        return digest(self.to_canonical())
