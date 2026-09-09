"""Outcome ledger: append-only, hash-chained.

Each entry's hash covers (seq, prev_hash, event, payload, vclock). Wall clock
is recorded on the entry but EXCLUDED from the hash, so a deterministic replay
of the same inputs produces a byte-identical chain regardless of when it ran.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .canon import digest
from .vclock import VectorClock

GENESIS = "0" * 64


@dataclass(frozen=True)
class LedgerEntry:
    seq: int
    prev_hash: str
    event: str
    payload: dict
    vclock: VectorClock
    wall_clock: float
    hash: str

    @staticmethod
    def compute_hash(seq: int, prev_hash: str, event: str, payload: dict, vclock: VectorClock) -> str:
        return digest({"seq": seq, "prev": prev_hash, "event": event, "payload": payload, "vclock": vclock})


class Ledger:
    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def head_hash(self) -> str:
        return self._entries[-1].hash if self._entries else GENESIS

    def append(self, event: str, payload: dict[str, Any], vclock: VectorClock, wall_clock: float) -> LedgerEntry:
        seq = len(self._entries)
        prev = self.head_hash()
        h = LedgerEntry.compute_hash(seq, prev, event, payload, vclock)
        e = LedgerEntry(seq, prev, event, payload, vclock, wall_clock, h)
        self._entries.append(e)
        return e

    def chain(self) -> tuple[str, ...]:
        return tuple(e.hash for e in self._entries)

    def verify(self) -> tuple[bool, Optional[int]]:
        """Return (ok, first_bad_seq)."""
        prev = GENESIS
        for i, e in enumerate(self._entries):
            if e.seq != i or e.prev_hash != prev:
                return False, i
            if LedgerEntry.compute_hash(e.seq, e.prev_hash, e.event, e.payload, e.vclock) != e.hash:
                return False, i
            prev = e.hash
        return True, None

    def events(self, event: str) -> tuple[LedgerEntry, ...]:
        return tuple(e for e in self._entries if e.event == event)
