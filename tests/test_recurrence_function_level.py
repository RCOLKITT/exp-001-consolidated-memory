import json

from phase0.corpus import Task
from phase0.functions import FunctionIndexCache
from phase0.ground_truth import gold_symbols
from phase2.recurrence import analyse, dir_of

SRC = "def parse(s):\n    return s\n\n\ndef dump(s):\n    return s\n"


def _t(i, start):
    return Task(instance_id=f"o__r-{i}", repo="o/r", base_commit="c", created_at=f"2025-01-{i:02d}T00:00:00Z", problem_statement="p",
                patch=f"diff --git a/pkg/m.py b/pkg/m.py\n--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -{start},1 +{start},1 @@\n-a\n+b\n")


def test_function_level_recurrence_counts_symbols_and_groups_by_file():
    idx = FunctionIndexCache(lambda repo, commit, path: SRC)
    tasks = [_t(1, 1), _t(2, 5), _t(3, 1), _t(4, 5), _t(5, 1), _t(6, 6)]     # parse, dump, parse, dump | eval: parse, dump
    res = analyse(tasks, ["o/r"], [4], gold_of=lambda t: gold_symbols(t, idx))
    row = res["o/r"]["rows"][0]
    assert row["prefix"] == 4 and row["files_ge2"] == 2 and row["distinct_files"] == 2         # two symbols, each seen twice
    assert row["eval_file_seen2"] == 1.0 and row["eval_dir_seen1"] == 1.0                     # dir columns = file-level at function level
    assert dir_of("pkg/m.py::parse") == "pkg/m.py" and dir_of("pkg/m.py") == "pkg"
    file_res = analyse(tasks, ["o/r"], [4])
    assert file_res["o/r"]["rows"][0]["distinct_files"] == 1
