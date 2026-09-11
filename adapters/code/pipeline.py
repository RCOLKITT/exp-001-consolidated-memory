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
    if flag.location.symbol:                      # v2: function-level pattern keys on (path, qualname)
        path_tokens = f"{path_tokens} # {flag.location.symbol}"
    return f"{symptom} => {path_tokens} :: {flag.pattern_text}".strip()


@dataclass(frozen=True)
class ArmSpec:
    """An evaluation arm: which memory version it sees and its retrieval gate τ
    (memories below τ are not injected; τ = 0 injects the top-k as in v1).
    kind: "control" (no memory), "memory", or "placebo" — the placebo arm
    injects as many lines as the primary treatment arm would at this task,
    but drawn (by the same retrieval similarity) from an irrelevant pool."""
    name: str
    version: Optional[str]
    tau: float = 0.0
    kind: str = "memory"


def parse_arms(spec: str, default_tau: float) -> list[ArmSpec]:
    """`control,treatment:0,gated:0.5,placebo:0` -> ArmSpecs. τ defaults: treatment
    -> default_tau, ungated -> 0, others -> default_tau. Version is a marker
    ("memory") that the caller replaces with the frozen version or "rolling"."""
    out = []
    for item in [x.strip() for x in spec.split(",") if x.strip()]:
        name, _, tau = item.partition(":")
        if name == "control":
            out.append(ArmSpec("control", None, 0.0, "control")); continue
        t = float(tau) if tau else (0.0 if name == "ungated" else default_tau)
        out.append(ArmSpec(name, "memory", t, "placebo" if name == "placebo" else "memory"))
    names = [a.name for a in out]
    if "control" not in names or "treatment" not in names or len(set(names)) != len(names):
        raise ValueError("--arms must include control and treatment, names unique")
    return out


@dataclass
class ArmResult:
    arm: str
    version: Optional[str]
    flags_by_task: dict[str, tuple[Flag, ...]] = field(default_factory=dict)
    retrieved_by_task: dict[str, tuple[str, ...]] = field(default_factory=dict)   # memory ids injected
    errors: dict[str, str] = field(default_factory=dict)                          # task -> error (excluded from every arm)
    file_flags_by_task: dict[str, tuple[Flag, ...]] = field(default_factory=dict) # v2: stage-1 file flags (secondary metric)
    scores_by_task: dict[str, dict[str, float]] = field(default_factory=dict)     # memory id -> retrieval score (all candidates)
    tau: float = 0.0
    version_by_task: dict[str, Optional[str]] = field(default_factory=dict)       # rolling mode: memory version this arm saw per task

    def metrics(self, truth: GroundTruth, repo_of) -> ArmMetrics:
        return score(self.flags_by_task, truth, repo_of)

    def file_metrics(self, truth: GroundTruth, repo_of) -> ArmMetrics:
        return score(self.file_flags_by_task or self.flags_by_task, truth, repo_of)

    def hits(self, truth: GroundTruth) -> dict[str, bool]:
        out = {}
        for iid, flags in self.flags_by_task.items():
            gt = truth.locations(iid)
            if gt:
                out[iid] = any(f.location.overlaps(h) for f in flags for h in gt)
        return out

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
        index_of: Optional[Callable[[Task, str], object]] = None,
        tau: float = 0.0,
        placebo_pool: Sequence[str] = (),
    ) -> None:
        self.repo = repo
        self.localizer = localizer
        self.truth = truth
        self.list_files = list_files
        self.index_of = index_of          # v2: (task, path) -> function spans at base_commit
        self.tau = tau                    # learning-phase retrieval gate (evaluation arms carry their own)
        self.placebo_pool = tuple(placebo_pool)   # irrelevant memories (another repository's), for the placebo arm
        self._flags: dict[str, Flag] = {}                       # record id -> Flag (oracle input)
        self.oracle = LocationOracle(truth, self._flags)
        self.kernel = Kernel(config, similarity, self.oracle, clock=clock, retrieval_similarity=retrieval_similarity)
        self.agent_id = f"verifier:{localizer.model}"
        self.agent_clock = VectorClock.zero()
        self.frozen_version: Optional[str] = None

    # -- one verifier pass ---------------------------------------------------
    def _retrieve(self, task: Task, tau: Optional[float] = None) -> tuple[list[str], tuple[str, ...], dict[str, float]]:
        """Top-k memories for the issue; only those scoring > 0 and ≥ τ are injected.
        Returns (contents, injected ids, scores of every candidate)."""
        tau = self.tau if tau is None else tau
        hits = self.kernel.retrieve(task.problem_statement)
        keep = [(m, s) for m, s in hits if s > 0.0 and s >= tau]
        return [m.content for m, _ in keep], tuple(m.id for m, _ in keep), {m.id: round(s, 6) for m, s in hits}

    def _placebo(self, task: Task, n: int) -> tuple[list[str], tuple[str, ...], dict[str, float]]:
        """Top-n of the placebo pool by the retrieval similarity — same count and
        selection rule as the treatment arm, content that cannot be relevant."""
        if n <= 0 or not self.placebo_pool:
            return [], (), {}
        sim = self.kernel.retrieval_similarity
        scored = sorted(((sim.sim(task.problem_statement, m), i) for i, m in enumerate(self.placebo_pool)), key=lambda x: (-x[0], x[1]))[:n]
        return [self.placebo_pool[i] for _, i in scored], tuple(f"placebo:{i}" for _, i in scored), {f"placebo:{i}": round(s_, 6) for s_, i in scored}

    def _localize(self, task: Task, memories: Sequence[str]):
        if getattr(self.localizer, "level", "file") == "function":
            return self.localizer.localize(task.instance_id, task.problem_statement, self.list_files(task), memories,
                                           index_of=(lambda p: self.index_of(task, p)) if self.index_of else None)
        return self.localizer.localize(task.instance_id, task.problem_statement, self.list_files(task), memories)

    def _records(self, task: Task, flags: Sequence[Flag]) -> list[Record]:
        # The verifier read the kernel's memory before acting: merge, then tick.
        self.agent_clock = self.agent_clock.merge(self.kernel.vclock).tick(self.agent_id)
        input_hash = digest({"instance_id": task.instance_id, "base_commit": task.base_commit})
        out = []
        for i, f in enumerate(flags):
            rid = digest({"task": task.instance_id, "rank": i, "path": f.location.path, **({"symbol": f.location.symbol} if f.location.symbol else {})})
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
            memories, _, _ = self._retrieve(t)
            try:
                flags = self._localize(t, memories).flags()
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
    def evaluate(self, eval_tasks: Sequence[Task], seed: int, version: Optional[str] = None, tau: Optional[float] = None) -> tuple[ArmResult, ArmResult]:
        """v1 two-arm evaluation: control (no memory) vs treatment (frozen version)."""
        version = version or self.frozen_version
        arms = self.evaluate_arms(eval_tasks, seed, (ArmSpec("control", None), ArmSpec("treatment", version, self.tau if tau is None else tau)))
        return arms["control"], arms["treatment"]

    def evaluate_arms(self, eval_tasks: Sequence[Task], seed: int, specs: Sequence[ArmSpec]) -> dict[str, ArmResult]:
        """Every arm on every task; arm order shuffled per task, task order
        randomised by seed. A task that fails in any arm is excluded from all
        of them, so every arm scores exactly the same task set (pairing)."""
        results = {sp.name: ArmResult(sp.name, sp.version, tau=sp.tau) for sp in specs}
        rng = random.Random(seed)
        order = list(eval_tasks)
        rng.shuffle(order)                                     # randomised task order
        for t in order:
            arm_order = list(specs)
            rng.shuffle(arm_order)                             # interleaved
            got = {}
            try:
                n_primary = None
                for sp in arm_order:
                    if sp.kind == "placebo":
                        if n_primary is None:
                            ref = next(x for x in specs if x.name == "treatment")
                            self.kernel.pin(ref.version); n_primary = len(self._retrieve(t, ref.tau)[1]) if ref.version else 0
                        memories, ids, scores = self._placebo(t, n_primary)
                    else:
                        self.kernel.pin(sp.version)
                        memories, ids, scores = self._retrieve(t, sp.tau) if sp.version else ([], (), {})
                    got[sp.name] = (self._localize(t, memories), ids, scores)
            except Exception as e:  # excluded from every arm: pairing is preserved
                msg = f"{type(e).__name__}: {str(e)[:300]}"
                for r in results.values():
                    r.errors[t.instance_id] = msg
                continue
            for name, (res, ids, scores) in got.items():
                r = results[name]
                r.flags_by_task[t.instance_id] = res.flags()
                r.retrieved_by_task[t.instance_id] = ids
                r.scores_by_task[t.instance_id] = scores
                if hasattr(res, "file_flags"):
                    r.file_flags_by_task[t.instance_id] = res.file_flags()
        return results

    # -- Design A: prequential / rolling evaluation (v2 draft §12) ---------------
    def rolling(self, tasks: Sequence[Task], warmup: int, seed: int, specs: Sequence[ArmSpec], learn: bool = True, max_consecutive_failures: int = 10) -> dict[str, ArmResult]:
        """Every task after `warmup` is an eval task scored against the memory
        built from every task before it (the pinned snapshot after task t-1).
        Order of operations per task, fixed:
          1. every arm localizes task t (control: no memory; memory arms: the
             snapshot as of t-1, gated by their τ); arm order shuffled by seed;
          2. the CONTROL arm's flags become records and are ingested — the
             learning stream never depends on memory's own effect;
          3. tick; a promotion takes a new snapshot which becomes visible at t+1.
        A task that fails in any arm is excluded from every arm's score but,
        if its control call succeeded, still feeds learning (the stream is a
        property of the corpus, not of the evaluation). `learn=False` is the
        negative control: memory stays empty and every arm equals control."""
        if self.kernel.frozen:
            raise RuntimeError("kernel already frozen")
        if not any(sp.version is None for sp in specs):
            raise ValueError("rolling evaluation needs a control arm (version None)")
        tasks = sorted(tasks, key=lambda t: (t.created_at, t.instance_id))
        results = {sp.name: ArmResult(sp.name, "rolling" if sp.version else None, tau=sp.tau) for sp in specs}
        self.learn_errors = {}
        self.n_warmup = min(warmup, len(tasks))
        rng = random.Random(seed)
        control_spec = next(sp for sp in specs if sp.version is None)
        consecutive = 0
        for i, t in enumerate(tasks):
            if consecutive >= max_consecutive_failures:              # circuit breaker: a dead key or endpoint, not a task problem
                raise RuntimeError(f"{consecutive} consecutive task failures at {t.instance_id}; last: {failure}")
            version = self.kernel.pinned_version                      # memory as of tasks < i (None until the first promotion)
            is_eval = i >= warmup
            order = list(specs)
            if is_eval:
                rng.shuffle(order)                                    # interleaved
            else:
                order = [control_spec]
            got, failure = {}, None
            n_primary = None
            for sp in order:
                try:
                    if sp.version is None:
                        self.kernel.pin(None)
                        memories, ids, scores = [], (), {}
                    elif sp.kind == "placebo":
                        if n_primary is None:
                            ref = next(x for x in specs if x.name == "treatment")
                            self.kernel.pin(version); n_primary = len(self._retrieve(t, ref.tau)[1]) if version else 0
                        memories, ids, scores = self._placebo(t, n_primary)
                    else:
                        self.kernel.pin(version)
                        memories, ids, scores = self._retrieve(t, sp.tau) if version else ([], (), {})
                    got[sp.name] = (self._localize(t, memories), ids, scores)
                except Exception as e:
                    failure = f"{type(e).__name__}: {str(e)[:300]}"
                    break
            if failure is not None and control_spec.name not in got:
                try:                                                  # the learning stream must not depend on arm order
                    self.kernel.pin(None)
                    got[control_spec.name] = (self._localize(t, []), (), {})
                except Exception as e:
                    failure = f"{type(e).__name__}: {str(e)[:300]}"
            consecutive = consecutive + 1 if failure is not None else 0
            self.kernel.pin(version)
            if learn:
                if control_spec.name in got:
                    for r in self._records(t, got[control_spec.name][0].flags()):
                        self.kernel.ingest(r)
                else:
                    self.learn_errors[t.instance_id] = failure or "control arm failed"
                res = self.kernel.tick()
                if res.promotion and res.promotion.promoted:
                    self.kernel.pin(self.kernel.snapshot())           # visible from the next task on
            if not is_eval:
                continue
            if failure is not None:
                for r in results.values():
                    r.errors[t.instance_id] = failure
                continue
            for name, (res_, ids, scores) in got.items():
                r = results[name]
                r.flags_by_task[t.instance_id] = res_.flags()
                r.retrieved_by_task[t.instance_id] = ids
                r.scores_by_task[t.instance_id] = scores
                r.version_by_task[t.instance_id] = version if name != control_spec.name else None
                if next(x for x in specs if x.name == name).kind == "placebo":
                    r.version_by_task[t.instance_id] = None
                if hasattr(res_, "file_flags"):
                    r.file_flags_by_task[t.instance_id] = res_.file_flags()
        self.frozen_version = self.kernel.freeze()
        return results

    def memory_locations(self) -> dict[str, str]:
        """memory id -> `path::symbol` (or `path`) of its source flags — the
        location a memory names, read from provenance, not parsed from text."""
        out = {}
        for o in self.kernel.store.all():
            for rid in o.provenance:
                f = self._flags.get(rid)
                if f is not None:
                    out[o.id] = f"{f.location.path}::{f.location.symbol}" if f.location.symbol else f.location.path
                    break
        return out

    def gold_keys(self, tasks: Sequence[Task]) -> dict[str, list[str]]:
        """instance_id -> gold `path::symbol` keys (None-gold tasks omitted)."""
        out = {}
        for t in tasks:
            try:
                gt = self.truth.locations(t.instance_id)
            except Exception:          # gold unresolvable (no checkout): the task was excluded from scoring anyway
                continue
            if gt:
                out[t.instance_id] = sorted({f"{h.path}::{h.symbol}" if h.symbol else h.path for h in gt})
        return out

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
            **({"n_warmup": self.n_warmup} if hasattr(self, "n_warmup") else {}),
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
