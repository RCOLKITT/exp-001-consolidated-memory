from phase2.baseline_agentless import compute


def test_hit_at_k_and_fp():
    gold = {"a": ("pkg/x.py",), "b": ("pkg/y.py", "pkg/z.py")}
    loc = [{"instance_id": "a", "found_files": ["pkg/q.py", "pkg/x.py", "pkg/r.py"]},
           {"instance_id": "b", "found_files": ["pkg/q.py"]},
           {"instance_id": "zz", "found_files": ["w.py"]}]
    r1, r3 = compute(loc, gold, 1), compute(loc, gold, 3)
    assert r1["n"] == 2 and r1["hit"] == 0 and r3["hit"] == 1 and r3["hit_at_k"] == 0.5
    assert r3["flags"] == 4 and r3["false_positive_rate"] == 0.75 and r3["missing_gold"] == 1
