import pytest

from phase0.freshness_gate import filter_tasks, latest_cutoff


MODELS = {"model-a": "2025-03-01", "model-b": "2025-06-30"}


def test_cutoff_is_the_latest_of_all_models():
    assert str(latest_cutoff(MODELS)) == "2025-06-30"


def test_only_strictly_later_tasks_admitted():
    tasks = [
        {"instance_id": "old", "created_at": "2025-06-30"},      # equal: rejected
        {"instance_id": "new", "created_at": "2025-07-01T10:00:00Z"},
        {"instance_id": "undated"},                              # rejected
        {"instance_id": "between", "created_at": "2025-05-01"},  # fresh for a, stale for b: rejected
    ]
    accepted, rejected = filter_tasks(tasks, MODELS)
    assert [t["instance_id"] for t, _ in accepted] == ["new"]
    assert {v.instance_id for _, v in rejected} == {"old", "undated", "between"}


def test_margin_pushes_threshold_out():
    tasks = [{"instance_id": "x", "created_at": "2025-07-05"}]
    assert filter_tasks(tasks, MODELS, margin_days=10)[0] == []
    assert len(filter_tasks(tasks, MODELS, margin_days=4)[0]) == 1


def test_no_models_is_an_error():
    with pytest.raises(ValueError):
        latest_cutoff({})
