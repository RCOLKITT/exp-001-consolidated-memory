import json

import pytest

from adapters.code.oracle import GroundTruth, Location
from phase0.metrics import lift, score
from phase0.verifier import CachedClient, Localizer, ModelRequest, ScriptedClient, render_prompt, repo_file_tree

FILES = ["pkg/a.py", "pkg/b.py", "pkg/c.py"]


def test_localizer_filters_unknown_and_duplicate_paths():
    resp = json.dumps({"files": [{"path": "pkg/b.py", "reason": "r"}, {"path": "ghost.py", "reason": ""},
                                 {"path": "pkg/b.py", "reason": "dup"}, {"path": "pkg/a.py", "reason": "r2"}]})
    loc = Localizer(ScriptedClient({"*": resp}), model="m", k=2)
    res = loc.localize("i1", "issue text", FILES)
    assert [p for p, _ in res.ranked] == ["pkg/b.py", "pkg/a.py"]
    flags = res.flags()
    assert flags[0].location.overlaps(Location("pkg/b.py", 120, 130))


def test_cache_makes_rerun_identical_and_offline(tmp_path):
    inner = ScriptedClient({"*": json.dumps({"files": [{"path": "pkg/a.py", "reason": "x"}]})})
    cache = tmp_path / "cache.jsonl"
    a = Localizer(CachedClient(inner, cache), "m").localize("i", "q", FILES)
    assert inner.calls == 1
    # second client, same cache, offline: identical output, no model call
    c2 = CachedClient(None, cache, offline=True)
    b = Localizer(c2, "m").localize("i", "q", FILES)
    assert a == b and c2.hits == 1 and inner.calls == 1
    with pytest.raises(LookupError):
        Localizer(c2, "m").localize("i", "different question", FILES)


def test_request_key_is_stable_and_sensitive():
    r1 = ModelRequest("m", "s", "u", {"a": 1})
    r2 = ModelRequest("m", "s", "u", {"a": 1})
    r3 = ModelRequest("m", "s", "u2", {"a": 1})
    assert r1.key() == r2.key() != r3.key()


def test_prompt_has_memory_section_only_in_treatment():
    ctrl = render_prompt("issue", FILES, 3)
    treat = render_prompt("issue", FILES, 3, memories=["off-by-one in pkg/a.py"])
    assert "Relevant memory" not in ctrl and "Relevant memory" in treat
    # treatment differs from control only by the memory section (spec Phase 4: memory is the only delta)
    assert treat.replace("## Relevant memory from prior defects in this repository\n- off-by-one in pkg/a.py\n\n", "") == ctrl


def test_repo_file_tree_skips_git_and_sorts(tmp_path):
    (tmp_path / ".git").mkdir(); (tmp_path / ".git" / "x.py").write_text("")
    (tmp_path / "pkg").mkdir(); (tmp_path / "pkg" / "b.py").write_text(""); (tmp_path / "pkg" / "a.py").write_text("")
    (tmp_path / "README.md").write_text("")
    assert repo_file_tree(tmp_path) == ["pkg/a.py", "pkg/b.py"]


def _flag(iid, path):
    from adapters.code.oracle import Flag
    return Flag(iid, Location(path, 1, 10**9), "")


def test_paired_metrics_and_lift():
    truth = GroundTruth({"t1": (Location("pkg/a.py", 5, 9),), "t2": (Location("pkg/b.py", 1, 2),), "t3": (Location("x.py", 1, 1),)})
    repo_of = {"t1": "r1", "t2": "r1", "t3": "r2"}
    control = score({"t1": [_flag("t1", "pkg/a.py"), _flag("t1", "pkg/c.py")], "t2": [_flag("t2", "pkg/c.py")], "t3": []}, truth, repo_of)
    assert control.n_tasks == 3 and control.n_localized == 1 and control.n_flags == 3 and control.n_false_positive == 2
    assert control.localization_rate == pytest.approx(1 / 3) and control.false_positive_rate == pytest.approx(2 / 3)
    assert control.per_repo["r1"]["n_localized"] == 1 and control.per_repo["r2"]["n_tasks"] == 1
    treatment = score({"t1": [_flag("t1", "pkg/a.py")], "t2": [_flag("t2", "pkg/b.py")], "t3": [_flag("t3", "x.py")]}, truth, repo_of)
    l = lift(treatment, control)
    assert l["localization_lift_pts"] == pytest.approx(66.67, abs=0.01) and l["false_positive_rise_pts"] == pytest.approx(-66.67, abs=0.01)
