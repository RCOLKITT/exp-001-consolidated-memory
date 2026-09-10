import csv
import json
import math

import pytest

from phase2.handcheck import agreement, export, sample_flags
from phase2.power import mde_at, n_per_arm


def test_power_matches_textbook_value():
    # classic: p0=0.5 -> 0.65, alpha .05 two-sided, power .8 ≈ 170 per arm
    assert 165 <= n_per_arm(0.5, 0.15) <= 175
    assert n_per_arm(0.5, 0.30) < n_per_arm(0.5, 0.15)
    assert abs(mde_at(0.5, n_per_arm(0.5, 0.15)) - 0.15) < 0.01
    assert math.isnan(mde_at(0.5, 5))
    with pytest.raises(ValueError):
        n_per_arm(0.9, 0.2)


def test_handcheck_export_and_agreement(tmp_path):
    patch = "diff --git a/pkg/a.py b/pkg/a.py\n--- a/pkg/a.py\n+++ b/pkg/a.py\n@@ -1,2 +1,2 @@\n-x\n+y\n"
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text(json.dumps({"instance_id": "o__r-1", "repo": "o/r", "base_commit": "c", "created_at": "2025-08-01",
                                 "problem_statement": "p", "patch": patch}) + "\n")
    flags = tmp_path / "flags.jsonl"
    flags.write_text(json.dumps({"instance_id": "o__r-1", "repo": "o/r", "ranked": [["pkg/a.py", "r"], ["pkg/b.py", "r"]], "request_key": "k"}) + "\n")
    out = tmp_path / "hc.csv"
    export(str(flags), str(tasks), n=50, seed=1, out=str(out))
    rows = list(csv.DictReader(open(out)))
    assert {(r["flagged_path"], r["oracle"]) for r in rows} == {("pkg/a.py", "bad"), ("pkg/b.py", "good")}
    # simulate manual labels: one agrees, one disagrees
    for r in rows:
        r["manual"] = r["oracle"] if r["flagged_path"] == "pkg/a.py" else "bad"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    assert agreement(str(out)) == (0.5, 1, 2)
    assert sample_flags([json.loads(flags.read_text())], 1, 0) == sample_flags([json.loads(flags.read_text())], 1, 0)


def test_independent_parser_agrees_with_oracle_parser_on_ordinary_patches():
    from phase0.ground_truth import gold_files
    from phase2.handcheck import independent_gold_files
    patch = ("diff --git a/pkg/a.py b/pkg/a.py\n--- a/pkg/a.py\n+++ b/pkg/a.py\n@@ -1,2 +1,2 @@\n-x\n+y\n"
             "diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1 @@\n-x\n+y\n"
             "diff --git a/pkg/gone.py b/pkg/gone.py\ndeleted file mode 100644\n--- a/pkg/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n")
    assert independent_gold_files(patch) == set(gold_files(patch)) == {"pkg/a.py", "pkg/gone.py"}
