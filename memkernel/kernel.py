"""Kernel orchestration: ingest -> surprise gate -> buffer -> scheduled
promotion -> versioned store, with every step written to the ledger.

Every public mutation is also appended to `self.trace` so the run can be
replayed (see `memkernel.replay`). Determinism contract: given the same
config, the same seam implementations, and the same trace, two kernels
produce identical ledger chains and identical store contents.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from .buffer import EpisodicBuffer
from .gates import PromotionGate, PromotionPolicy, PromotionResult, SurpriseDecision, SurpriseGate
from .ledger import Ledger
from .records import MemoryObject, Record
from .seams import Contradiction, Oracle, Similarity
from .store import MemoryStore
from .vclock import VectorClock


class KernelError(RuntimeError):
    pass


def counting_clock(start: float = 1_700_000_000.0, step: float = 1.0) -> Callable[[], float]:
    """Deterministic wall clock for reproducible runs. Wall clock is recorded,
    never used for ordering, and excluded from every hash — so this only
    makes ledgers human-comparable across runs."""
    n = -1

    def _clock() -> float:
        nonlocal n
        n += 1
        return start + n * step

    return _clock


@dataclass(frozen=True)
class KernelConfig:
    theta_surprise: float = 0.35
    # A non-admitted candidate reinforces its nearest buffered entry only if
    # max_similarity >= reinforce_min_sim; otherwise it is discarded outright.
    # None means "same bar as admission" (1 - theta): every redundant candidate
    # reinforces. A higher bar keeps promoted memories purer at the cost of
    # fewer reinforcements (docs/DECISIONS.md D22).
    reinforce_min_sim: Optional[float] = None
    ttl_ticks: int = 50
    retrieval_k: int = 5
    agent_id: str = "kernel"
    approver_id: str = "promotion-gate"
    policy: PromotionPolicy = field(default_factory=PromotionPolicy)

    def to_canonical(self) -> dict:
        return {
            "theta_surprise": self.theta_surprise,
            "reinforce_min_sim": self.reinforce_min_sim,
            "ttl_ticks": self.ttl_ticks,
            "retrieval_k": self.retrieval_k,
            "agent_id": self.agent_id,
            "approver_id": self.approver_id,
            "policy": self.policy.to_canonical(),
        }


@dataclass(frozen=True)
class IngestResult:
    record: Record
    decision: SurpriseDecision
    retrieved: tuple[tuple[MemoryObject, float], ...]
    outcome: str  # buffered | reinforced | discarded


@dataclass(frozen=True)
class TickResult:
    tick: int
    expired: tuple[str, ...]
    promotion: Optional[PromotionResult]


# Trace events: ("ingest", Record) | ("tick",) | ("promote",) | ("freeze",) | ("pin", version) | ("supersede", old_id, MemoryObject)
Event = tuple


class Kernel:
    def __init__(
        self,
        config: KernelConfig,
        similarity: Similarity,
        oracle: Oracle,
        contradiction: Optional[Contradiction] = None,
        store: Optional[MemoryStore] = None,
        ledger: Optional[Ledger] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self.similarity = similarity
        self.oracle = oracle
        self.store = store or MemoryStore()
        self.ledger = ledger or Ledger()
        self.buffer = EpisodicBuffer(config.ttl_ticks)
        self.surprise_gate = SurpriseGate(similarity, config.theta_surprise)
        self.promotion_gate = PromotionGate(similarity, config.policy, contradiction)
        self._clock = clock
        self.tick_count = 0
        self.vclock = VectorClock.zero()
        self.pinned_version: Optional[str] = None
        self.frozen = False
        self.trace: list[Event] = []
        self.ledger.append("init", {"config": config.to_canonical()}, self.vclock, self._clock())

    # -- helpers ----------------------------------------------------------
    def _now(self) -> float:
        return self._clock()

    def _advance(self, agent_id: Optional[str] = None) -> VectorClock:
        self.vclock = self.vclock.tick(agent_id or self.config.agent_id)
        return self.vclock

    def _visible_memory(self) -> tuple[MemoryObject, ...]:
        return self.store.at(self.pinned_version)

    # -- retrieval --------------------------------------------------------
    def retrieve(self, query: str, k: Optional[int] = None) -> tuple[tuple[MemoryObject, float], ...]:
        """Top-k promoted memories from the pinned version. Empty if unpinned
        (control arm: memory_version = None)."""
        k = k or self.config.retrieval_k
        scored = [(m, self.similarity.sim(query, m.content)) for m in self._visible_memory()]
        scored.sort(key=lambda ms: (-ms[1], ms[0].id))
        hits = tuple(scored[:k])
        self.ledger.append(
            "retrieve",
            {"version": self.pinned_version, "hits": [[m.id, round(s, 12)] for m, s in hits]},
            self.vclock,
            self._now(),
        )
        return hits

    # -- ingest -----------------------------------------------------------
    def ingest(self, record: Record) -> IngestResult:
        self.trace.append(("ingest", record))
        self.vclock = self.vclock.merge(record.vclock)
        self._advance()
        labeled = record.with_label(self.oracle.label(record))
        retrieved = self.retrieve(labeled.content)
        comparanda = list(self.buffer.contents()) + [(m.id, m.content) for m in self._visible_memory()]
        decision = self.surprise_gate.evaluate(labeled, comparanda)
        outcome = "discarded"
        if decision.admitted:
            self.buffer.add(labeled, self.tick_count, decision.surprise)
            outcome = "buffered"
        elif (decision.nearest_id is not None and decision.nearest_id in self.buffer
              and decision.max_similarity >= (self.config.reinforce_min_sim if self.config.reinforce_min_sim is not None else 1.0 - self.config.theta_surprise)):
            # Redundant to a buffered entry and similar enough to count as the same pattern: evidence.
            self.buffer.reinforce(decision.nearest_id, labeled)
            outcome = "reinforced"
        # Redundant to promoted memory: discarded; the ledger keeps nearest_id
        # so retrieval hit rate can be computed later without touching memory.
        self.ledger.append(
            "ingest",
            {"record": labeled, "decision": decision, "tick": self.tick_count, "outcome": outcome},
            self.vclock,
            self._now(),
        )
        return IngestResult(labeled, decision, retrieved, outcome)

    # -- time -------------------------------------------------------------
    def tick(self) -> TickResult:
        self.trace.append(("tick",))
        self.tick_count += 1
        self._advance()
        expired = tuple(e.record.id for e in self.buffer.expire(self.tick_count))
        if expired:
            self.ledger.append("expire", {"tick": self.tick_count, "record_ids": list(expired)}, self.vclock, self._now())
        promotion = None
        if not self.frozen and self.tick_count % self.config.policy.schedule_every_ticks == 0:
            promotion = self._promote()
        return TickResult(self.tick_count, expired, promotion)

    # -- promotion --------------------------------------------------------
    def promote(self) -> PromotionResult:
        """Run the promotion gate now (out of schedule). Refused once frozen."""
        self.trace.append(("promote",))
        return self._promote()

    def _promote(self) -> PromotionResult:
        if self.frozen:
            raise KernelError("memory is frozen; promotion is disabled")
        vc = self._advance(self.config.approver_id)
        result = self.promotion_gate.run(
            self.buffer.entries(), self.store.live(), self.config.approver_id, vc, self._now()
        )
        for obj in result.promoted:
            self.store.put(obj)
        self.buffer.remove(result.consumed)
        self.ledger.append(
            "promote",
            {
                "tick": self.tick_count,
                "promoted": [o.id for o in result.promoted],
                "rejected": [[list(r.record_ids), r.reason] for r in result.rejected],
            },
            vc,
            self._now(),
        )
        return result

    # -- versioning -------------------------------------------------------
    def supersede(self, old_id: str, content: str, note: str = "") -> MemoryObject:
        """Replace a promoted memory with a new object. The old object is kept."""
        old = self.store.get(old_id)
        vc = self._advance(self.config.approver_id)
        new = MemoryObject(
            content=content,
            provenance=old.provenance,
            input_hashes=old.input_hashes,
            labels=old.labels,
            proposed_by=old.proposed_by,
            approved_by=self.config.approver_id,
            vclock=vc,
            wall_clock=self._now(),
            supersedes=old_id,
            note=note,
        )
        self.trace.append(("supersede", old_id, content, note))
        new_id = self.store.supersede(old_id, new)
        self.ledger.append("supersede", {"old": old_id, "new": new_id, "note": note}, vc, self._now())
        return new

    def freeze(self) -> str:
        """Pin the current live memory as a version and disable promotion."""
        self.trace.append(("freeze",))
        vc = self._advance()
        version = self.store.freeze()
        self.frozen = True
        self.pinned_version = version
        self.ledger.append("freeze", {"version": version, "live": list(self.store.live_ids())}, vc, self._now())
        return version

    def snapshot(self) -> str:
        """Record a version without freezing (promotion continues)."""
        self.trace.append(("snapshot",))
        vc = self._advance()
        version = self.store.freeze()
        self.ledger.append("snapshot", {"version": version, "live": list(self.store.live_ids())}, vc, self._now())
        return version

    def pin(self, version: Optional[str]) -> None:
        """Select which memory version ingest/retrieve see. None = no memory."""
        if version is not None and version not in self.store.versions():
            raise KernelError(f"unknown version {version}")
        self.trace.append(("pin", version))
        vc = self._advance()
        self.pinned_version = version
        self.ledger.append("pin", {"version": version}, vc, self._now())

    # -- replay support ---------------------------------------------------
    def apply(self, event: Event) -> None:
        kind = event[0]
        if kind == "ingest":
            self.ingest(event[1])
        elif kind == "tick":
            self.tick()
        elif kind == "promote":
            self.promote()
        elif kind == "freeze":
            self.freeze()
        elif kind == "snapshot":
            self.snapshot()
        elif kind == "pin":
            self.pin(event[1])
        elif kind == "supersede":
            self.supersede(event[1], event[2], event[3])
        else:
            raise KernelError(f"unknown trace event {kind!r}")
