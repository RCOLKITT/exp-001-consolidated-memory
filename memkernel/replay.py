"""Deterministic replay: rebuild a kernel from a trace and compare."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .kernel import Event, Kernel


@dataclass(frozen=True)
class ReplayReport:
    identical: bool
    ledger_chain_equal: bool
    store_ids_equal: bool
    versions_equal: bool
    buffer_equal: bool


def replay(trace: Sequence[Event], factory: Callable[[], Kernel]) -> Kernel:
    k = factory()
    for ev in trace:
        k.apply(ev)
    return k


def _buffer_shape(k: Kernel):
    return tuple((e.record.id, e.inserted_tick, tuple(r.id for r in e.support)) for e in k.buffer.entries())


def compare(a: Kernel, b: Kernel) -> ReplayReport:
    chain = a.ledger.chain() == b.ledger.chain()
    ids = tuple(o.id for o in a.store.all()) == tuple(o.id for o in b.store.all())
    versions = a.store.versions() == b.store.versions()
    buf = _buffer_shape(a) == _buffer_shape(b)
    return ReplayReport(chain and ids and versions and buf, chain, ids, versions, buf)
