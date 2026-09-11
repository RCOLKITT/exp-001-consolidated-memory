"""v2 pipeline: retrieval gate τ, N-arm pairing, function-level learn/evaluate
with function-keyed consolidation. Fully offline."""
import json

from adapters.code.oracle import Location
from adapters.code.pipeline import ArmSpec, RepoPipeline, record_content
from adapters.code.similarity import FunctionKeyedSimilarity
from memkernel import KernelConfig, PromotionPolicy
from memkernel.seams import TokenJaccardSimilarity
from phase0.corpus import Task
from phase0.functions import FunctionIndexCache, Span
from phase0.ground_truth import function_ground_truth_from_tasks
from phase0.verifier import Flag, LocalizerV2, ModelRequest, schema_key
from tests.conftest import fixed_clock
from tests.test_pipeline import RepeatingVerifier, _pipeline, _task

FILES = ["pkg/parser.py", "pkg/io.py"]
SRC = "def parse(s):\n    return s\n\n\ndef dump(s):\n    return s\n"          # parse: 1-2, dump: 5-6
INDEX = {"pkg/parser.py": (Span("parse", "function", 1, 2), Span("dump", "function", 5, 6)), "pkg/io.py": ()}


def _fpatch(path, start):
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -{start},1 +{start},1 @@\n-a\n+b\n"


def _ftask(i, start=1):
    return Task(instance_id=f"o__r-{i}", repo="o/r", base_commit="c", created_at=f"2025-08-{i:02d}T00:00:00Z",
                problem_statement=f"issue {i}", patch=_fpatch("pkg/parser.py", start))


class FunctionVerifier:
    """Stage 1 always ranks parser.py; stage 2 flags `parse` and `dump` without
    memory, and only `parse` when memory is shown (so the delta is visible)."""

    def __init__(self):
        self.calls = 0

    def complete(self, req: ModelRequest) -> str:
        self.calls += 1
        if schema_key(req.schema) == "files":
            return json.dumps({"files": [{"path": "pkg/parser.py", "reason": "r"}]})
        if "Relevant memory" in req.user:
            return json.dumps({"functions": [{"path": "pkg/parser.py", "qualname": "parse", "reason": "memory"}]})
        return json.dumps({"functions": [{"path": "pkg/parser.py", "qualname": "parse", "reason": "r"}, {"path": "pkg/parser.py", "qualname": "dump", "reason": "guess"}]})


def _fpipeline(tasks, tau=0.0):
    cache = FunctionIndexCache(lambda repo, commit, path: SRC if path == "pkg/parser.py" else None)
    truth = function_ground_truth_from_tasks(tasks, cache)
    cfg = KernelConfig(ttl_ticks=100, policy=PromotionPolicy(schedule_every_ticks=1, min_occurrences=2, min_distinct_inputs=2, cluster_similarity=0.6, eligible_labels=frozenset({"bad"})))
    loc = LocalizerV2(FunctionVerifier(), "m", k=2)
    sem = TokenJaccardSimilarity()
    p = RepoPipeline("o/r", loc, FunctionKeyedSimilarity(sem), truth, cfg, lambda t: FILES, fixed_clock(),
                     retrieval_similarity=sem, index_of=lambda t, path: cache.spans(t.repo, t.base_commit, path), tau=tau)
    return p, truth


def test_record_content_carries_symbol_and_function_keyed_seam_separates_functions():
    a = record_content(Flag("i", Location("pkg/parser.py", 1, 2, "parse"), "why"), "crash on parse")
    b = record_content(Flag("i", Location("pkg/parser.py", 5, 6, "dump"), "why"), "crash on parse")
    c = record_content(Flag("i", Location("pkg/parser.py", 1, 2, "parse"), "other reason"), "different symptom")
    assert a == "crash on parse => pkg / parser # parse :: why"
    seam = FunctionKeyedSimilarity()
    assert seam.sim(a, c) == 1.0 and seam.sim(a, b) == 0.0                  # same function ⇒ same pattern; same file ≠ same pattern


def test_function_level_learn_promotes_recurring_function_only_and_treatment_uses_it():
    build = [_ftask(i, start=1) for i in range(1, 5)]                          # gold: parse (lines 1-2) every time
    ev = [_ftask(i, start=1) for i in range(10, 14)]
    p, truth = _fpipeline(build + ev)
    version = p.learn(build)
    live = p.kernel.store.live()
    assert len(live) == 1 and "# parse" in live[0].content                    # `dump` was wrong every time: label good, never promoted
    control, treatment = p.evaluate(ev, seed=1, version=version)
    hc, ht = control.hits(truth), treatment.hits(truth)
    assert len(hc) == len(ht) == 4 and all(hc.values()) and all(ht.values())
    assert all(len(v) == 2 for v in control.flags_by_task.values()) and all(len(v) == 1 for v in treatment.flags_by_task.values())   # memory removed the wrong flag
    mc, mt = control.metrics(truth, {t.instance_id: "o/r" for t in ev}), treatment.metrics(truth, {t.instance_id: "o/r" for t in ev})
    assert mc.false_positive_rate == 0.5 and mt.false_positive_rate == 0.0
    fc = control.file_metrics(truth, {t.instance_id: "o/r" for t in ev})
    assert fc.localization_rate == 1.0 and fc.n_flags == 4                    # file-level secondary from stage-1 flags


def test_tau_above_one_never_injects_and_arms_are_identical():
    build = [_ftask(i) for i in range(1, 5)]
    ev = [_ftask(i) for i in range(10, 13)]
    p, truth = _fpipeline(build + ev)
    version = p.learn(build)
    control, gated = p.evaluate(ev, seed=3, version=version, tau=1.01)
    assert all(v == () for v in gated.retrieved_by_task.values())
    assert all(gated.scores_by_task[t.instance_id] for t in ev)              # candidates were scored, just not injected
    assert gated.flags_by_task == control.flags_by_task


def test_three_arms_share_one_task_set_and_gated_sits_between():
    build = [_ftask(i) for i in range(1, 5)]
    ev = [_ftask(i) for i in range(10, 14)]
    p, truth = _fpipeline(build + ev)
    version = p.learn(build)
    arms = p.evaluate_arms(ev, 5, (ArmSpec("control", None), ArmSpec("treatment", version, 0.0), ArmSpec("ungated", version, 0.0), ArmSpec("never", version, 1.01)))
    keys = [set(a.flags_by_task) for a in arms.values()]
    assert all(k == keys[0] for k in keys) and len(keys[0]) == 4
    assert arms["treatment"].flags_by_task == arms["ungated"].flags_by_task and arms["never"].flags_by_task == arms["control"].flags_by_task


def test_failing_task_is_dropped_from_every_arm():
    class Flaky(FunctionVerifier):
        def complete(self, req):
            if "issue 11" in req.user:
                raise RuntimeError("boom")
            return super().complete(req)
    build = [_ftask(i) for i in range(1, 5)]
    ev = [_ftask(i) for i in range(10, 14)]
    p, truth = _fpipeline(build + ev)
    p.localizer = LocalizerV2(Flaky(), "m", k=2)
    version = p.learn(build)
    arms = p.evaluate_arms(ev, 5, (ArmSpec("control", None), ArmSpec("treatment", version), ArmSpec("ungated", version)))
    for a in arms.values():
        assert "o__r-11" in a.errors and "o__r-11" not in a.flags_by_task and len(a.flags_by_task) == 3
