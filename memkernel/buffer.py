"""Episodic buffer with TTL. Forgetting is the default.

TTL is measured in kernel ticks (logical time), not wall-clock seconds, so
expiry is deterministic under replay. Wall clock is never consulted.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from .records import Record


@dataclass(frozen=True)
class BufferEntry:
    record: Record
    inserted_tick: int
    surprise: float
    # Records judged redundant to this entry by the surprise gate. Redundancy
    # is evidence: it is not written as a new entry, but it is not thrown away
    # either — it becomes provenance for promotion. `support` includes `record`.
    support: tuple[Record, ...] = ()

    @property
    def occurrences(self) -> int:
        return len(self.support)


class EpisodicBuffer:
    def __init__(self, ttl_ticks: int) -> None:
        if ttl_ticks < 1:
            raise ValueError("ttl_ticks must be >= 1")
        self.ttl_ticks = ttl_ticks
        self._entries: dict[str, BufferEntry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, record_id: str) -> bool:
        return record_id in self._entries

    def add(self, record: Record, tick: int, surprise: float) -> BufferEntry:
        if record.id in self._entries:
            raise ValueError(f"record {record.id} already buffered")
        e = BufferEntry(record=record, inserted_tick=tick, surprise=surprise, support=(record,))
        self._entries[record.id] = e
        return e

    def reinforce(self, entry_id: str, record: Record) -> BufferEntry:
        """Attach a redundant record as supporting evidence. No new entry, no
        mutation: the entry is replaced by a new frozen value."""
        old = self._entries[entry_id]
        if any(r.id == record.id for r in old.support):
            raise ValueError(f"record {record.id} already supports {entry_id}")
        new = replace(old, support=old.support + (record,))
        self._entries[entry_id] = new
        return new

    def entries(self) -> tuple[BufferEntry, ...]:
        return tuple(self._entries.values())  # insertion order

    def contents(self) -> tuple[tuple[str, str], ...]:
        return tuple((e.record.id, e.record.content) for e in self._entries.values())

    def expire(self, now_tick: int) -> tuple[BufferEntry, ...]:
        dead = tuple(e for e in self._entries.values() if now_tick - e.inserted_tick >= self.ttl_ticks)
        for e in dead:
            del self._entries[e.record.id]
        return dead

    def remove(self, record_ids: Iterable[str]) -> None:
        for rid in record_ids:
            self._entries.pop(rid, None)
