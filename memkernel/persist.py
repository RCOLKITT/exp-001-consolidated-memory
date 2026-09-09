"""Save / load a kernel between phases (freeze in Phase 3, pin in Phase 4).

Everything is content-addressed, so a loaded store reproduces the same ids
and versions; the ledger is re-verified on load.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canon import canonical
from .kernel import Kernel
from .ledger import Ledger, LedgerEntry
from .records import MemoryObject
from .store import MemoryStore
from .vclock import VectorClock


def _obj_to_dict(o: MemoryObject) -> dict[str, Any]:
    d = o.to_canonical()
    d["wall_clock"] = o.wall_clock
    return d


def _obj_from_dict(d: dict[str, Any]) -> MemoryObject:
    return MemoryObject(
        content=d["content"], provenance=tuple(d["provenance"]), input_hashes=tuple(d["input_hashes"]),
        labels=tuple(d["labels"]), proposed_by=tuple(d["proposed_by"]), approved_by=d["approved_by"],
        vclock=VectorClock.of(d["vclock"]), wall_clock=float(d["wall_clock"]), kind=d.get("kind", "promoted"),
        supersedes=d.get("supersedes"), note=d.get("note", ""),
    )


def dump_kernel(k: Kernel) -> dict[str, Any]:
    store = k.store
    return {
        "config": k.config.to_canonical(),
        "tick_count": k.tick_count,
        "vclock": k.vclock.to_canonical(),
        "pinned_version": k.pinned_version,
        "frozen": k.frozen,
        "objects": [_obj_to_dict(o) for o in store.all()],
        "superseded_by": dict(store._superseded_by),
        "versions": [[v, list(store._versions[v])] for v in store.versions()],
        "ledger": [
            {"seq": e.seq, "prev_hash": e.prev_hash, "event": e.event, "payload": json.loads(canonical(e.payload)),
             "vclock": e.vclock.to_canonical(), "wall_clock": e.wall_clock, "hash": e.hash}
            for e in k.ledger.entries()
        ],
    }


def save_kernel(k: Kernel, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dump_kernel(k), sort_keys=True))


def load_kernel(path: str | Path, k: Kernel) -> Kernel:
    """Restore state into a freshly constructed kernel `k` (same config and seams)."""
    d = json.loads(Path(path).read_text())
    if d["config"] != k.config.to_canonical():
        raise ValueError("kernel config differs from the saved one")
    store = MemoryStore()
    for od in d["objects"]:
        store.put(_obj_from_dict(od))
    store._superseded_by = dict(d["superseded_by"])
    for v, ids in d["versions"]:
        store._versions[v] = tuple(ids)
        store._version_order.append(v)
    ledger = Ledger()
    for e in d["ledger"]:
        ledger._entries.append(LedgerEntry(e["seq"], e["prev_hash"], e["event"], e["payload"], VectorClock.of(e["vclock"]), e["wall_clock"], e["hash"]))
    ok, bad = ledger.verify()
    if not ok:
        raise ValueError(f"ledger failed verification at seq {bad}")
    k.store = store
    k.ledger = ledger
    k.tick_count = d["tick_count"]
    k.vclock = VectorClock.of(d["vclock"])
    k.pinned_version = d["pinned_version"]
    k.frozen = d["frozen"]
    return k
