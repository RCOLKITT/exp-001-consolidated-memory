from phase2.check_config import check

REG = {"stage": "rolling", "tau": 0.5, "repos": ["a/b", "c/d", "n/c"], "shards": {"A": ["a/b"], "B": ["c/d", "n/c"]}}


def test_shard_config_passes_and_design_change_fails():
    assert check(REG, {**REG, "repos": ["a/b"], "shard": "A", "resume_run": 10}) == []
    assert check(REG, {**REG, "repos": ["a/b"], "shard": "B"}) == ["shard B does not match its registered repo list"]
    assert any(p.startswith("tau:") for p in check(REG, {**REG, "tau": 0.0}))
    assert check(REG, {**REG, "repos": ["zzz"]}) == ["repos is neither the registered list nor one of its shards"]
