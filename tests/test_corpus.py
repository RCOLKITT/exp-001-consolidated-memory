import json

import pytest

from phase0.corpus import Task, apply_freshness, normalise, read_tasks, write_tasks

RAW = {"instance_id": "owner__repo-12", "repo": "owner/repo", "base_commit": "deadbeef", "created_at": "2025-07-01T00:00:00Z",
       "problem_statement": "it breaks", "patch": "diff --git a/x.py b/x.py\n", "FAIL_TO_PASS": '["t::a"]', "hints_text": None}


def test_normalise_and_docker_image():
    t = normalise(RAW)
    assert t.fail_to_pass == ("t::a",) and t.hints_text == ""
    assert t.docker_image == "starryzhang/sweb.eval.x86_64.owner_1776_repo-12"
    with pytest.raises(ValueError):
        normalise({**RAW, "patch": ""})


def test_roundtrip_and_freshness(tmp_path):
    old = normalise({**RAW, "instance_id": "owner__repo-1", "created_at": "2025-01-01"})
    p = tmp_path / "tasks.jsonl"
    write_tasks([normalise(RAW), old], p)
    tasks = read_tasks(p)
    assert [t.instance_id for t in tasks] == ["owner__repo-12", "owner__repo-1"]
    models = tmp_path / "models.json"
    models.write_text(json.dumps({"claude-opus-5": "2025-03-01"}))
    fresh = apply_freshness(tasks, models, tmp_path / "fresh.jsonl")
    assert [t.instance_id for t in fresh] == ["owner__repo-12"]
    assert len((tmp_path / "fresh.jsonl").read_text().splitlines()) == 2
