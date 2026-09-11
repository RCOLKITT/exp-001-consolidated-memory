"""Placebo arm, arm-spec parsing, placebo pool, shard aggregation, paired baseline."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from adapters.code.pipeline import ArmSpec, parse_arms
from memkernel.persist import save_kernel
from phase4.aggregate import aggregate
from phase4.placebo_pool import build
from tests.test_pipeline_v2 import _fpipeline, _ftask

POOL = ["auth fails on refresh => other / repo / auth # Session.refresh :: token expiry", "crash on parse => other / repo / io # Reader.read :: bad offset"]
SPECS = (ArmSpec("control", None, 0.0, "control"), ArmSpec("treatment", "rolling", 0.0), ArmSpec("placebo", "rolling", 0.0, "placebo"))


def test_parse_arms():
    specs = parse_arms("control,treatment:0,gated:0.5,placebo:0", default_tau=0.7)
    assert [(a.name, a.tau, a.kind) for a in specs] == [("control", 0.0, "control"), ("treatment", 0.0, "memory"), ("gated", 0.5, "memory"), ("placebo", 0.0, "placebo")]
    assert parse_arms("control,treatment", 0.7)[1].tau == 0.7 and parse_arms("control,treatment,ungated", 0.7)[2].tau == 0.0
    with pytest.raises(ValueError):
        parse_arms("control,gated", 0.0)
    with pytest.raises(ValueError):
        parse_arms("control,treatment,treatment", 0.0)


def test_placebo_arm_matches_treatment_count_with_irrelevant_content():
    tasks = [_ftask(i) for i in range(1, 8)]
    p, _ = _fpipeline(tasks)
    p.placebo_pool = tuple(POOL)
    seen = []
    orig = p._localize
    def spy(task, memories):
        seen.append((task.instance_id, tuple(memories))); return orig(task, memories)
    p._localize = spy
    arms = p.rolling(tasks, warmup=0, seed=1, specs=SPECS)
    c, t, pl = arms["control"], arms["treatment"], arms["placebo"]
    ids = [x.instance_id for x in tasks]
    # before the first promotion the treatment injects nothing, so the placebo injects nothing and equals control
    assert pl.retrieved_by_task[ids[0]] == () and pl.flags_by_task[ids[0]] == c.flags_by_task[ids[0]]
    # afterwards: same count as treatment, content from the pool, ids marked placebo
    for i in ids[2:]:
        assert len(pl.retrieved_by_task[i]) == len(t.retrieved_by_task[i]) == 1 and pl.retrieved_by_task[i][0].startswith("placebo:")
    placebo_prompts = [m for iid, m in seen if m and any(x in POOL for x in m)]
    assert placebo_prompts and all(all(x in POOL for x in m) for m in placebo_prompts)
    assert all(v is None for v in pl.version_by_task.values())
    assert len(p.kernel.ledger.events("ingest")) == 14                       # learning still from control flags only (7 tasks x 2)


def test_placebo_pool_builder_and_shard_aggregate(tmp_path):
    tasks = [_ftask(i) for i in range(1, 6)]
    p, truth = _fpipeline(tasks)
    p.rolling(tasks, warmup=1, seed=1, specs=SPECS[:2])
    kd = tmp_path / "runs" / "o__r"; kd.mkdir(parents=True)
    save_kernel(p.kernel, kd / "kernel.json")
    pool = build([kd / "kernel.json"])
    assert pool["n"] == 1 and "# parse" in pool["pool"][0]["content"] and pool["sources"] == ["o/r"] and len(pool["sha256"]) == 64


def test_aggregate_over_shards_equals_single_run(tmp_path):
    from phase4.report import Aggregator, arms_json
    tasks = [_ftask(i) for i in range(1, 8)]
    reports = {}
    for repo, neg in (("o/r", False), ("n/c", True)):
        p, truth = _fpipeline(tasks)
        p.repo = repo
        arms = p.rolling(tasks, warmup=2, seed=1, specs=SPECS[:2], learn=not neg)
        repo_of = {t.instance_id: repo for t in tasks[2:]}
        aj = arms_json(arms, truth, repo_of, "function", {"mode": "rolling", "warmup": 2})
        d = tmp_path / ("a" if not neg else "b"); d.mkdir()
        (d / f"{repo.replace('/', '__')}.arms.json").write_text(json.dumps(aj))
        reports[repo] = (arms, truth, repo_of, aj)
    single = Aggregator(["control", "treatment"], "function", 0.0)
    for repo, (arms, truth, repo_of, aj) in reports.items():
        single.add(repo, arms, truth, repo_of, aj, repo == "n/c")
    one = single.report()
    merged = aggregate([tmp_path / "a", tmp_path / "b"], "n/c", tmp_path / "out")
    for k in ("localization_lift_pts", "false_positive_rise_pts", "per_repo_lift", "negative_control_lift", "control", "treatment"):
        assert merged[k] == one[k], k
    assert (tmp_path / "out" / "o__r.arms.json").exists() and (tmp_path / "out" / "gate4.json").exists()
    with pytest.raises(SystemExit):
        aggregate([tmp_path / "a", tmp_path / "a"], None, tmp_path / "out2")      # a repo in two shards is refused


def test_paired_baseline_placebo(tmp_path):
    from phase4.paired import analyse
    a = {"arms": {"control": {"hits": {"t1": False, "t2": False}, "flags": {"t1": ["a"], "t2": ["a"]}, "retrieved": {}},
                  "treatment": {"hits": {"t1": True, "t2": False}, "flags": {"t1": ["b"], "t2": ["a"]}, "retrieved": {"t1": ["m"]}},
                  "placebo": {"hits": {"t1": True, "t2": True}, "flags": {"t1": ["b"], "t2": ["c"]}, "retrieved": {"t1": ["placebo:0"]}}}}
    d = tmp_path / "ev"; d.mkdir(); (d / "o__r.arms.json").write_text(json.dumps(a))
    vs_control = analyse(None, d, None, [], "treatment")
    vs_placebo = analyse(None, d, None, [], "treatment", baseline="placebo")
    assert vs_control["primary"]["lift_pts"] == 50.0 and vs_placebo["primary"]["lift_pts"] == -50.0 and vs_placebo["baseline"] == "placebo"
