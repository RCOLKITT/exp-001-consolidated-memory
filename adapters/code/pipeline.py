"""Wire the three seams to the kernel for one repository (spec Phase 2 item 5).

One kernel per repo: memory is codebase-specific (spec §1, no cross-repo).

Phase 3 `learn`   — build-split tasks, chronological; localize with whatever
                    memory is promoted so far, oracle labels the flags, every
                    flag becomes a Record ingested through the surprise gate;
                    one kernel tick per task, promotion on the tick schedule;
                    freeze at the end and pin the version.
Phase 4 `evaluate` — eval-split tasks; both arms on every task, arm order
                    interleaved and task order randomised by seed. Control
                    pins memory_version=None; treatment pins the frozen
                    version. Memory retrieval is the only delta.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

from memkernel import Kernel, KernelConfig
from memkernel.canon import digest
from memkernel.records import Record
from memkernel.seams import Similarity
from memkernel.vclock import VectorClock
from phase0.corpus import Task
from phase0.metrics import ArmMetrics, lift, score
from phase0.verifier import Localizer

from .oracle import Flag, GroundTruth, LocationOracle

FileLister = Callable[[Task], Sequence[str]]   # task -> repo file tree at base_commit


def issue_head(problem_statement: str, limit: int = 200) -> str:
    """The issue's first non-empty line (its title on GitHub), truncated."""
    for line in problem_statement.strip().splitlines():
        if line.strip():
            return line.strip()[:limit]
    return ""


def record_content(flag: Flag, symptom: str) -> str:
    """Defect-pattern text the similarity seam compares and retrieval matches:
    `symptom => location :: reason`. The symptom (issue head) is what a future
    issue can match against; the location is what memory is for (D12)."""
    path_tokens = flag.location.path.replace("/", " / ").replace(".py", "")
    return f"{symptom} => {path_tokens} :: {flag.pattern_text}".strip()


@dataclass
class ArmResult:
    arm: str
    version: Optional[str]
    flags_by_task: dict[str, tuple[Flag, ...]] = field(default_factory=dict)
    retrieved_by_task: dict[str, tuple[str, ...]] = field(default_factory=dict)   # memory ids shown
    errors: dict[str, str] = field(default_factory=dict)                          # task -> error (excluded from both arms)

    def metrics(self, truth: GroundTruth, repo_of) -> ArmMetrics:
        return score(self.flags_by_task, truth, repo_of)

    @property
    def retrieval_hit_rate(self) -> float:
        n = len(self.retrieved_by_task)
        return sum(1 for v in self.retrieved_by_task.values() if v) / n if n else 0.0


class RepoPipeline:
    def __init__(
        self,
        repo: str,
        localizer: Localizer,
        similarity: Similarity,
        truth: GroundTruth,
        config: KernelConfig,
        list_files: FileLister,
        clock: Callable[[], float],
        retrieval_similarity: Optional[Similarity] = None,
    ) -> None:
        self.repo = repo
        self.localizer = localizer
        self.truth = truth
        self.list_files = list_files
        self._flags: dict[str, Flag] = {}                       # record id -> Flag (oracle input)
        self.oracle = LocationOracle(truth, self._flags)
        self.kernel = Kernel(config, similarity, self.oracle, clock=clock, retrieval_similarity=retrieval_similarity)
        self.agent_id = f"verifier:{localizer.model}"
        self.agent_clock = VectorClock.zero()
        self.frozen_version: Optional[str] = None

    # -- one verifier pass ---------------------------------------------------
    def _retrieve(self, task: Task) -> tuple[list[str], tuple[str, ...]]:
        hits = self.kernel.retrieve(task.problem_statement)
        return [m.content for m, s in hits if s > 0.0], tuple(m.id for m, s in hits if s > 0.0)

    def _localize(self, task: Task, memories: Sequence[str]) -> tuple[Flag, ...]:
        res = self.localizer.localize(task.instance_id, task.problem_statement, self.list_files(task), memories)
        return res.flags()

    def _records(self, task: Task, flags: Sequence[Flag]) -> list[Record]:
        # The verifier read the kernel's memory before acting: merge, then tick.
        self.agent_clock = self.agent_clock.merge(self.kernel.vclock).tick(self.agent_id)
        input_hash = digest({"instance_id": task.instance_id, "base_commit": task.base_commit})
        out = []
        for i, f in enumerate(flags):
            rid = digest({"task": task.instance_id, "rank": i, "path": f.location.path})
            self._flags[rid] = f
            out.append(Record(id=rid, content=record_content(f, issue_head(task.problem_statement)), input_hash=input_hash, agent_id=self.agent_id,
                              vclock=self.agent_clock, wall_clock=self.kernel._now()))
        return out

    # -- Phase 3 ---------------------------------------------------------------
    def learn(self, build_tasks: Sequence[Task]) -> str:
        if self.kernel.frozen:
            raise RuntimeError("kernel already frozen")
        tasks = sorted(build_tasks, key=lambda t: (t.created_at, t.instance_id))
        self.learn_errors: dict[str, str] = {}
        for t in tasks:
            memories, _ = self._retrieve(t)
            try:
                flags = self._localize(t, memories)
            except Exception as e:  # skip the task; it contributes no records and is reported
                self.learn_errors[t.instance_id] = f"{type(e).__name__}: {str(e)[:300]}"
                self.kernel.tick()
                continue
            for r in self._records(t, flags):
                self.kernel.ingest(r)
            res = self.kernel.tick()
            if res.promotion and res.promotion.promoted:
                # newly promoted memory becomes visible to the next task
                self.kernel.pin(self.kernel.snapshot())
        self.frozen_version = self.kernel.freeze()
        return self.frozen_version

    # -- Phase 4 ---------------------------------------------------------------
    def evaluate(self, eval_tasks: Sequence[Task], seed: int, version: Optional[str] = None) -> tuple[ArmResult, ArmResult]:
        version = version or self.frozen_version
        control, treatment = ArmResult("control", None), ArmResult("treatment", version)
        rng = random.Random(seed)
        order = list(eval_tasks)
        rng.shuffle(order)                                     # randomised task order
        for i, t in enumerate(order):
            arms = [control, treatment] if (i + rng.randrange(2)) % 2 == 0 else [treatment, control]   # interleaved
            results = {}
            try:
                for arm in arms:
                    self.kernel.pin(arm.version)
                    memories, ids = self._retrieve(t) if arm.version else ([], ())
                    results[arm.arm] = (self._localize(t, memories), ids)
            except Exception as e:  # a task that fails in either arm is excluded from both: pairing is preserved
                msg = f"{type(e).__name__}: {str(e)[:300]}"
                control.errors[t.instance_id] = msg; treatment.errors[t.instance_id] = msg
                continue
            for arm in (control, treatment):
                arm.flags_by_task[t.instance_id], arm.retrieved_by_task[t.instance_id] = results[arm.arm]
        return control, treatment

    # -- Learning-phase diagnostics (Gate 3) -------------------------------------
    def gate3_stats(self) -> dict:
        ingests = self.kernel.ledger.events("ingest")
        n = len(ingests)
        buffered = sum(1 for e in ingests if e.payload["outcome"] == "buffered")
        return {
            "candidate_writes": n,
            "buffered": buffered,
            "discarded_or_reinforced": n - buffered,
            "discard_rate": round((n - buffered) / n, 4) if n else 0.0,
            "promoted": len(self.kernel.store.live()),
            "frozen_version": self.frozen_version,
            "learn_errors": getattr(self, "learn_errors", {}),
        }


def gate4_report(control: ArmMetrics, treatment: ArmMetrics, per_repo_lift: dict, negative_control_lift: Optional[dict]) -> dict:
    majority = sum(1 for v in per_repo_lift.values() if v["localization_lift_pts"] > 0) > len(per_repo_lift) / 2 if per_repo_lift else False
    overall = lift(treatment, control)
    return {
        "control": control.to_json(), "treatment": treatment.to_json(), **overall,
        "per_repo_lift": per_repo_lift, "effect_in_majority_of_repos": majority,
        "negative_control_lift": negative_control_lift,
    }


def write_json(obj, path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True))
