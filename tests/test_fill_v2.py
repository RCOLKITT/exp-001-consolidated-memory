from phase2.fill_v2 import fill


def test_fill_applies_the_registered_rules():
    rec = {"o/r": {"rows": [{"prefix": 20, "n_eval": 100, "eval_file_seen2": 0.4, "build_repeat_share": 0.3}]},
           "n/c": {"rows": [{"prefix": 20, "n_eval": 10, "eval_file_seen2": 0.9, "build_repeat_share": 0.9}]}}
    ctl = {"o/r": {"n_tasks": 20, "n_localized": 10}, "n/c": {"n_tasks": 20, "n_localized": 20}}
    f = fill(rec, ctl, {"o/r": 20, "n/c": 20}, "n/c", [])
    r = f["repos"]["o/r"]
    assert r["ceiling_pts"] == 20.0 and r["gate3_discard_floor"] == 0.15 and "n/c" not in f["repos"]
    assert f["eval_pool"] == 100 and f["p0"] == 0.5 and f["ceiling_pts"] == 20.0
    assert f["mde_pts"] is not None and f["kill_number_pts"] >= 10 and f["kill_number_pts"] >= f["mde_pts"]
    assert f["feasible"] == (20.0 >= 1.5 * f["mde_pts"])
