"""Mechanism assertion: supersession creates a new object; no mutation, no
reconsolidation."""
import dataclasses

import pytest

from memkernel import MemoryObject, MemoryStore, VectorClock
from memkernel.store import StoreError


def _obj(content, **kw):
    base = dict(
        content=content, provenance=("r1",), input_hashes=("a",), labels=("bad",),
        proposed_by=("x",), approved_by="gate", vclock=VectorClock.of({"gate": 1}), wall_clock=0.0,
    )
    base.update(kw)
    return MemoryObject(**base)


def test_objects_are_immutable_and_content_addressed():
    m = _obj("hello")
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.content = "bye"  # type: ignore[misc]
    assert _obj("hello").id == m.id
    assert _obj("hello", wall_clock=99.0).id == m.id      # wall clock not part of identity
    assert _obj("hello2").id != m.id


def test_supersession_keeps_old_object():
    s = MemoryStore()
    old = _obj("v1")
    s.put(old)
    new = _obj("v2", supersedes=old.id, vclock=VectorClock.of({"gate": 2}))
    s.supersede(old.id, new)
    assert s.get(old.id) == old                  # unchanged, still retrievable
    assert s.superseded_by(old.id) == new.id
    assert not s.is_live(old.id) and s.is_live(new.id)
    assert s.live() == (new,)


def test_supersession_is_single_shot_and_explicit():
    s = MemoryStore()
    old = _obj("v1"); s.put(old)
    with pytest.raises(StoreError):
        s.supersede(old.id, _obj("v2"))          # must declare supersedes
    s.supersede(old.id, _obj("v2", supersedes=old.id))
    with pytest.raises(StoreError):
        s.supersede(old.id, _obj("v3", supersedes=old.id))   # already superseded


def test_versions_are_snapshots_not_views():
    s = MemoryStore()
    a = _obj("a"); s.put(a)
    v1 = s.freeze()
    b = _obj("b", supersedes=a.id); s.supersede(a.id, b)
    v2 = s.freeze()
    assert s.at(v1) == (a,)                      # v1 still sees the old object
    assert s.at(v2) == (b,)
    assert s.at(None) == ()
    assert v1 != v2 and s.freeze() == v2         # freeze is idempotent on same live set
