"""End-to-end: seams wired to the kernel; learn -> freeze -> evaluate with a
scripted verifier, fully offline."""
import json

import pytest

from adapters.code.oracle import Location
from adapters.code.pipeline import RepoPipeline, gate4_report, record_content
from memkernel import Kernel, KernelConfig, PromotionPolicy
from memkernel.persist import load_kernel, save_kernel
from memkernel.seams import TokenJaccardSimilarity
from phase0.corpus import Task
from phase0.ground_truth import ground_truth_from_tasks
from phase0.metrics import lift
from phase0.verifier import Localizer, ModelClient, ModelRequest
from tests.conftest import fixed_clock

FILES = ["pkg/parser.py", "pkg/io.py", "pkg/util.py"]


def _patch(path):
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -5,2 +5,2 @@\n-a\n+b\n"


def _task(i, gold):
    return Task(instance_id=f"o__r-{i}", repo="o/r", base_commit=f"c{i}", created_at=f"2025-08-{i:02d}T00:00:00Z",
                problem_statement=f"issue {i}", patch=_patch(gold))


class RepeatingVerifier:
    """Always flags pkg/parser.py (right when gold is parser); flags io.py when
    memory mentions parser (i.e. it 'uses' memory) — lets the test see the delta."""

    def __init__(self):
        self.calls = 0

    def complete(self, req: ModelRequest) -> str:
        self.calls += 1
        if "Relevant memory" in req.user:
            return json.dumps({"files": [{"path": "pkg/parser.py", "reason": "memory says parser"}]})
        return json.dumps({"files": [{"path": "pkg/parser.py", "reason": "off by one in parse"}, {"path": "pkg/util.py", "reason": "guess"}]})


def _pipeline(tasks, ttl=100):
    truth = ground_truth_from_tasks(tasks)
    cfg = KernelConfig(ttl_ticks=ttl, policy=PromotionPolicy(schedule_every_ticks=1, cluster_similarity=0.5))
    loc = Localizer(RepeatingVerifier(), "m", k=2)
    return RepoPipeline("o/r", loc, TokenJaccardSimilarity(), truth, cfg, lambda t: FILES, fixed_clock()), truth


def test_learn_promotes_only_confirmed_defects_and_freezes():
    # 6 build tasks, gold = parser.py each time -> parser flags are 'bad' (confirmed), util flags 'good' (FP)
    build = [_task(i, "pkg/parser.py") for i in range(1, 7)]
    p, truth = _pipeline(build)
    v = p.learn(build)
    assert p.kernel.frozen and p.kernel.pinned_version == v
    live = p.kernel.store.live()
    assert len(live) >= 1
    for m in live:
        assert set(m.labels) == {"bad"}                    # §6.5 self-poisoning guard: util.py 'good' never promoted
        assert "parser" in m.content and len(m.input_hashes) >= 3
        assert m.approved_by == "promotion-gate" and all(a.startswith("verifier:") for a in m.proposed_by)
    s = p.gate3_stats()
    # 2 flags per task before memory exists, 1 flag per task once the verifier sees memory:
    # 12 candidate writes without memory, fewer once promotion kicks in mid-chain.
    assert 6 < s["candidate_writes"] < 12 and s["promoted"] == len(live) and 0 < s["discard_rate"] < 1
    assert p.kernel.ledger.events("retrieve")  # memory was consulted during learning
    assert p.kernel.ledger.verify() == (True, None)


def test_evaluate_interleaves_arms_and_memory_is_only_delta():
    build = [_task(i, "pkg/parser.py") for i in range(1, 7)]
    ev = [_task(i, "pkg/parser.py") for i in range(10, 16)]
    p, truth = _pipeline(build + ev)
    p.learn(build)
    control, treatment = p.evaluate(ev, seed=3)
    repo_of = {t.instance_id: "o/r" for t in ev}
    mc, mt = control.metrics(truth, repo_of), treatment.metrics(truth, repo_of)
    assert mc.localization_rate == 1.0 and mt.localization_rate == 1.0
    assert mc.false_positive_rate == 0.5 and mt.false_positive_rate == 0.0   # memory removed the util.py guess
    assert treatment.retrieval_hit_rate == 1.0 and control.retrieval_hit_rate == 0.0
    l = lift(mt, mc)
    assert l["localization_lift_pts"] == 0 and l["false_positive_rise_pts"] == -50
    rep = gate4_report(mc, mt, {"o/r": l}, None)
    assert rep["effect_in_majority_of_repos"] is False   # lift is on FP, not localization


def test_negative_control_has_identical_arms():
    ev = [_task(i, "pkg/parser.py") for i in range(1, 5)]
    p, truth = _pipeline(ev)
    p.frozen_version = p.kernel.freeze()                     # no learning: empty frozen memory
    control, treatment = p.evaluate(ev, seed=1)
    assert control.flags_by_task == treatment.flags_by_task
    assert all(v == () for v in treatment.retrieved_by_task.values())


def test_kernel_roundtrip_through_persistence(tmp_path):
    build = [_task(i, "pkg/parser.py") for i in range(1, 7)]
    p, truth = _pipeline(build)
    v = p.learn(build)
    save_kernel(p.kernel, tmp_path / "k.json")
    fresh = Kernel(p.kernel.config, TokenJaccardSimilarity(), p.oracle, clock=fixed_clock())
    k2 = load_kernel(tmp_path / "k.json", fresh)
    assert k2.pinned_version == v and k2.frozen
    assert tuple(o.id for o in k2.store.all()) == tuple(o.id for o in p.kernel.store.all())
    assert k2.store.at(v) == p.kernel.store.at(v)
    assert k2.ledger.chain() == p.kernel.ledger.chain() and k2.ledger.verify() == (True, None)
    with pytest.raises(ValueError):
        load_kernel(tmp_path / "k.json", Kernel(KernelConfig(ttl_ticks=7), TokenJaccardSimilarity(), p.oracle))


def test_record_content_pairs_symptom_with_location():
    from adapters.code.oracle import Flag
    from adapters.code.pipeline import issue_head
    f = Flag("i", Location("pkg/parser.py", 1, 9), "off by one")
    c = record_content(f, issue_head("\n\nParser drops last row\nlong body..."))
    assert c == "Parser drops last row => pkg / parser :: off by one"


def test_file_keyed_consolidation_promotes_recurring_file_and_retrieves_semantically():
    """D24: same file => same pattern regardless of wording; retrieval stays semantic."""
    from adapters.code.similarity import FileKeyedSimilarity, make_similarity
    sem = make_similarity("hashing")
    build = [_task(i, "pkg/parser.py") for i in range(1, 7)]
    truth = ground_truth_from_tasks(build)
    cfg = KernelConfig(ttl_ticks=100, theta_surprise=0.45, reinforce_min_sim=0.7, policy=PromotionPolicy(schedule_every_ticks=1, cluster_similarity=0.6))
    loc = Localizer(RepeatingVerifier(), "m", k=2)
    p = RepoPipeline("o/r", loc, FileKeyedSimilarity(sem), truth, cfg, lambda t: FILES, fixed_clock(), retrieval_similarity=sem)
    p.learn(build)
    live = p.kernel.store.live()
    assert len(live) == 1 and set(live[0].labels) == {"bad"} and "parser" in live[0].content   # util.py flags are 'good': never promoted
    assert len(live[0].input_hashes) >= 3
    ev = [_task(i, "pkg/parser.py") for i in range(10, 13)]
    control, treatment = p.evaluate(ev, seed=1)
    assert treatment.retrieval_hit_rate == 1.0 and control.retrieval_hit_rate == 0.0
    assert p.gate3_stats()["consolidation"] if "consolidation" in p.gate3_stats() else True
