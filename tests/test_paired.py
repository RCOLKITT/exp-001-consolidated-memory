import json
from pathlib import Path

from phase4.paired import analyse, mcnemar_exact_p, paired_ci


PATCH = "diff --git a/pkg/a.py b/pkg/a.py\n--- a/pkg/a.py\n+++ b/pkg/a.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"


def _task(iid, repo):
    return {"instance_id": iid, "repo": repo, "base_commit": "c", "created_at": "2024-01-01T00:00:00Z",
            "problem_statement": "p", "patch": PATCH}


def test_discordant_pairs_and_secondary(tmp_path: Path):
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("".join(json.dumps(_task(f"o__r-{i}", "o/r")) + "\n" for i in range(4))
                     + json.dumps(_task("n__c-1", "n/c")) + "\n")
    ev = tmp_path / "eval"; ev.mkdir()
    (ev / "o__r.arms.json").write_text(json.dumps({
        "control_flags": {"o__r-0": ["pkg/a.py"], "o__r-1": ["x.py"], "o__r-2": ["x.py"], "o__r-3": ["pkg/a.py"]},
        "treatment_flags": {"o__r-0": ["pkg/a.py"], "o__r-1": ["pkg/a.py"], "o__r-2": ["x.py"], "o__r-3": ["y.py"]},
        "retrieved": {"o__r-0": ["m"], "o__r-1": ["m"], "o__r-2": [], "o__r-3": ["m"]}, "errors": {}}))
    (ev / "n__c.arms.json").write_text(json.dumps({
        "control_flags": {"n__c-1": ["pkg/a.py"]}, "treatment_flags": {"n__c-1": ["pkg/a.py"]}, "retrieved": {}, "errors": {}}))
    rep = analyse(tasks, ev, "n/c", ["o/r"])
    p = rep["primary"]
    assert p["n_tasks"] == 4 and p["both_hit"] == 1 and p["treatment_only_hit"] == 1 and p["control_only_hit"] == 1 and p["neither_hit"] == 1
    assert p["lift_pts"] == 0.0 and p["flags_differed"] == 2 and p["retrieved_any"] == 3
    assert rep["negative_control"]["n_tasks"] == 1 and rep["negative_control"]["lift_pts"] == 0.0
    assert rep["secondary"]["n_tasks"] == 4


def test_mcnemar_and_ci():
    assert mcnemar_exact_p(0, 0) == 1.0 and mcnemar_exact_p(5, 5) == 1.0
    assert abs(mcnemar_exact_p(0, 5) - 2 * (1 / 32)) < 1e-9
    lo, hi = paired_ci(100, 10, 14)
    assert lo < 4.0 < hi
