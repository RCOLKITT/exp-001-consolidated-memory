"""Surprise gate and promotion gate.

Surprise gate (spec Phase 1, item 2):
    surprise = 1 - max_similarity(candidate, memory)
    admit to buffer iff surprise > theta_surprise

Promotion gate (spec §6): runs on a schedule, never continuously. A cluster of
buffered records is promoted only when ALL of:
    1. occurrence_count      >= min_occurrences   (eligible records only)
    2. distinct input hashes >= min_distinct_inputs
    3. no unresolved contradiction with an existing promoted memory
    4. separation of duties  — approver is not one of the proposers
    5. only records whose label is in `eligible_labels` count (default: bad)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from .buffer import BufferEntry
from .records import MemoryObject, Record
from .seams import Contradiction, NoContradiction, Similarity
from .vclock import VectorClock


# --------------------------------------------------------------------------
# Surprise gate
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class SurpriseDecision:
    record_id: str
    surprise: float
    max_similarity: float
    nearest_id: Optional[str]
    admitted: bool

    def to_canonical(self) -> dict:
        return {
            "record_id": self.record_id,
            "surprise": round(self.surprise, 12),
            "max_similarity": round(self.max_similarity, 12),
            "nearest_id": self.nearest_id,
            "admitted": self.admitted,
        }


class SurpriseGate:
    def __init__(self, similarity: Similarity, theta: float) -> None:
        if not 0.0 <= theta <= 1.0:
            raise ValueError("theta must be in [0,1]")
        self.similarity = similarity
        self.theta = theta

    def evaluate(self, candidate: Record, comparanda: Sequence[tuple[str, str]]) -> SurpriseDecision:
        best_sim, best_id = 0.0, None
        for cid, content in comparanda:
            s = self.similarity.sim(candidate.content, content)
            if s > best_sim:
                best_sim, best_id = s, cid
        surprise = 1.0 - best_sim
        return SurpriseDecision(
            record_id=candidate.id,
            surprise=surprise,
            max_similarity=best_sim,
            nearest_id=best_id,
            admitted=surprise > self.theta,
        )


# --------------------------------------------------------------------------
# Promotion gate
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PromotionPolicy:
    min_occurrences: int = 3
    min_distinct_inputs: int = 3
    eligible_labels: frozenset = field(default_factory=lambda: frozenset({"bad"}))
    cluster_similarity: float = 0.65        # sim >= this => same pattern
    require_separation_of_duties: bool = True
    schedule_every_ticks: int = 10          # promotion runs only on these ticks

    def to_canonical(self) -> dict:
        return {
            "min_occurrences": self.min_occurrences,
            "min_distinct_inputs": self.min_distinct_inputs,
            "eligible_labels": sorted(self.eligible_labels),
            "cluster_similarity": self.cluster_similarity,
            "require_separation_of_duties": self.require_separation_of_duties,
            "schedule_every_ticks": self.schedule_every_ticks,
        }


@dataclass(frozen=True)
class Rejection:
    record_ids: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class PromotionResult:
    promoted: tuple[MemoryObject, ...]
    rejected: tuple[Rejection, ...]
    # buffer entry ids consumed by promotion (removed from buffer)
    consumed: tuple[str, ...]


class PromotionGate:
    def __init__(
        self,
        similarity: Similarity,
        policy: PromotionPolicy,
        contradiction: Optional[Contradiction] = None,
    ) -> None:
        self.similarity = similarity
        self.policy = policy
        self.contradiction = contradiction or NoContradiction()

    def cluster(self, entries: Sequence[BufferEntry]) -> list[list[BufferEntry]]:
        """Greedy single-pass clustering by similarity to the cluster seed.

        Deterministic given entry order (buffer insertion order).
        """
        clusters: list[list[BufferEntry]] = []
        for e in entries:
            for c in clusters:
                if self.similarity.sim(e.record.content, c[0].record.content) >= self.policy.cluster_similarity:
                    c.append(e)
                    break
            else:
                clusters.append([e])
        return clusters

    def run(
        self,
        entries: Sequence[BufferEntry],
        promoted_memory: Sequence[MemoryObject],
        approver_id: str,
        vclock: VectorClock,
        wall_clock: float,
    ) -> PromotionResult:
        p = self.policy
        promoted: list[MemoryObject] = []
        rejected: list[Rejection] = []
        consumed: list[str] = []

        for c in self.cluster(entries):
            ids = tuple(e.record.id for e in c)
            # occurrences = every supporting record across the cluster
            eligible = [r for e in c for r in e.support if r.label in p.eligible_labels]
            if len(eligible) < p.min_occurrences:
                rejected.append(Rejection(ids, f"occurrences {len(eligible)} < {p.min_occurrences}"))
                continue
            inputs = sorted({r.input_hash for r in eligible})
            if len(inputs) < p.min_distinct_inputs:
                rejected.append(Rejection(ids, f"distinct_inputs {len(inputs)} < {p.min_distinct_inputs}"))
                continue
            proposers = sorted({r.agent_id for r in eligible})
            if p.require_separation_of_duties and approver_id in proposers:
                rejected.append(Rejection(ids, f"separation_of_duties: approver {approver_id} is a proposer"))
                continue
            seed = c[0].record.content
            contradicted = self.contradiction.contradicted(seed, promoted_memory)
            if contradicted:
                rejected.append(Rejection(ids, f"contradicts {','.join(contradicted)}"))
                continue
            obj = MemoryObject(
                content=seed,
                provenance=tuple(sorted(r.id for r in eligible)),
                input_hashes=tuple(inputs),
                labels=tuple(sorted(r.label for r in eligible)),
                proposed_by=tuple(proposers),
                approved_by=approver_id,
                vclock=vclock,
                wall_clock=wall_clock,
            )
            promoted.append(obj)
            consumed.extend(ids)

        return PromotionResult(tuple(promoted), tuple(rejected), tuple(consumed))
