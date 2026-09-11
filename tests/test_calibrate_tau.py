from phase2.calibrate_tau import calibrate, pairs_from_arms


def test_pairs_and_precision_rule():
    a = {"memory_locations": {"m1": "pkg/a.py::f", "m2": "pkg/b.py::g"}, "gold": {"t1": ["pkg/a.py::f"], "t2": ["pkg/b.py::g"]},
         "arms": {"ungated": {"scores": {"t1": {"m1": 0.8, "m2": 0.3}, "t2": {"m1": 0.4, "m2": 0.6}, "t3": {"m1": 0.9}}}}}
    pairs = pairs_from_arms(a, "ungated")
    assert sorted(pairs) == [(0.3, False), (0.4, False), (0.6, True), (0.8, True)]        # t3 has no gold: skipped
    res = calibrate(pairs)
    assert res["tau"] == 0.0 and res["rule"] == "precision >= 0.5"                        # precision 0.5 already at theta 0
    res2 = calibrate([(0.1, False), (0.2, False), (0.3, False), (0.55, True)])
    assert res2["tau"] == 0.25                                                            # at 0.25 the selection is {0.3 F, 0.55 T}: precision 0.5
    res3 = calibrate([(0.1, False), (0.2, False), (0.3, False), (0.4, False)])
    assert res3["tau"] == 0.4 and res3["rule"].startswith("90th percentile")
