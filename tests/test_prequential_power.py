from phase0.corpus import Task
from phase0.functions import FunctionIndexCache
from phase0.ground_truth import gold_symbols
from phase2.power import mde_at, mde_paired, n_paired
from phase2.prequential import analyse, keys_at

SRC = "class Box:\n    def a(self):\n        pass\n\n    def b(self):\n        pass\n\n\ndef top():\n    pass\n"


def _t(i, start):
    return Task(instance_id=f"o__r-{i}", repo="o/r", base_commit="c", created_at=f"2025-01-{i:02d}T00:00:00Z", problem_statement="p",
                patch=f"diff --git a/pkg/m.py b/pkg/m.py\n--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -{start},1 +{start},1 @@\n-a\n+b\n")


def test_keys_at_levels():
    syms = ("pkg/m.py::Box.a", "pkg/m.py::top", "pkg/m.py::<module>")
    assert keys_at("function", syms) == set(syms)
    assert keys_at("class", syms) == {"pkg/m.py::Box", "pkg/m.py::top", "pkg/m.py::<module>"}
    assert keys_at("file", syms) == {"pkg/m.py"}


def test_prequential_counts_each_task_against_everything_before_it():
    idx = FunctionIndexCache(lambda repo, commit, path: SRC)
    tasks = [_t(1, 2), _t(2, 5), _t(3, 2), _t(4, 9), _t(5, 5), _t(6, 2)]     # Box.a, Box.b, Box.a, top, Box.b, Box.a
    res = analyse(tasks, warmup=2, min_chain=3, gold_symbols_of=lambda t: gold_symbols(t, idx), exclude=set())
    r = res["repos"]["o/r"]
    assert r["chain"] == 6 and r["function"]["n_eval"] == 4
    assert r["function"]["seen1"] == 0.75 and r["function"]["seen2"] == 0.25          # tasks 3,5,6 seen>=1; task 6 seen>=2 (Box.a twice before)
    assert r["class"]["seen2"] == 0.75 and r["file"]["seen2"] == 1.0                   # Box seen twice by task 3; file always
    assert res["aggregate"]["function"]["n_eval"] == 4


def test_paired_mde_matches_unpaired_at_half_discordance_and_shrinks_with_concordance():
    assert abs(100 * mde_paired(0.5, 373) - 100 * mde_at(0.436, 373)) < 0.3
    assert mde_paired(0.1, 373) < mde_paired(0.3, 373) < mde_paired(0.5, 373)
    n = n_paired(0.3, 0.065)
    assert abs(mde_paired(0.3, n) - 0.065) < 0.002
