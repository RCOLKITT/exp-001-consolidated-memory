"""Content-addressed, versioned, append-only memory store.

Invariants (spec Phase 1, item 4):
- objects are immutable; `put` is idempotent on id
- supersession creates a NEW object pointing at the old one; the old object is
  retained and merely marked superseded in an index
- a version is the digest of the set of live object ids at freeze time;
  `at(version)` returns exactly that set, forever
"""
from __future__ import annotations

from typing import Optional

from .canon import digest
from .records import MemoryObject


class StoreError(RuntimeError):
    pass


class MemoryStore:
    def __init__(self) -> None:
        self._objects: dict[str, MemoryObject] = {}
        self._order: list[str] = []                 # insertion order, for determinism
        self._superseded_by: dict[str, str] = {}
        self._versions: dict[str, tuple[str, ...]] = {}
        self._version_order: list[str] = []

    # -- objects ---------------------------------------------------------
    def put(self, obj: MemoryObject) -> str:
        oid = obj.id
        existing = self._objects.get(oid)
        if existing is None:
            self._objects[oid] = obj
            self._order.append(oid)
        return oid

    def get(self, oid: str) -> MemoryObject:
        try:
            return self._objects[oid]
        except KeyError:
            raise StoreError(f"unknown memory id {oid}") from None

    def __contains__(self, oid: str) -> bool:
        return oid in self._objects

    def __len__(self) -> int:
        return len(self._objects)

    def all(self) -> tuple[MemoryObject, ...]:
        return tuple(self._objects[i] for i in self._order)

    # -- supersession ----------------------------------------------------
    def supersede(self, old_id: str, new_obj: MemoryObject) -> str:
        if old_id not in self._objects:
            raise StoreError(f"cannot supersede unknown id {old_id}")
        if new_obj.supersedes != old_id:
            raise StoreError("new object must declare supersedes=old_id")
        if old_id in self._superseded_by:
            raise StoreError(f"{old_id} already superseded by {self._superseded_by[old_id]}")
        new_id = self.put(new_obj)
        if new_id == old_id:
            raise StoreError("supersession must produce a distinct object")
        self._superseded_by[old_id] = new_id
        return new_id

    def superseded_by(self, oid: str) -> Optional[str]:
        return self._superseded_by.get(oid)

    def is_live(self, oid: str) -> bool:
        return oid in self._objects and oid not in self._superseded_by

    def live(self) -> tuple[MemoryObject, ...]:
        return tuple(self._objects[i] for i in self._order if i not in self._superseded_by)

    def live_ids(self) -> tuple[str, ...]:
        return tuple(sorted(i for i in self._order if i not in self._superseded_by))

    # -- versions --------------------------------------------------------
    def freeze(self) -> str:
        ids = self.live_ids()
        version = digest({"live": list(ids)})
        if version not in self._versions:
            self._versions[version] = ids
            self._version_order.append(version)
        return version

    def versions(self) -> tuple[str, ...]:
        return tuple(self._version_order)

    def at(self, version: Optional[str]) -> tuple[MemoryObject, ...]:
        """Memory visible at `version`. `None` means no memory (control arm)."""
        if version is None:
            return ()
        try:
            ids = self._versions[version]
        except KeyError:
            raise StoreError(f"unknown memory version {version}") from None
        return tuple(self._objects[i] for i in ids)
