"""Design A: prequential evaluation — memory as of t-1, learning from control flags only, pairing across arms."""
from adapters.code.pipeline import ArmSpec
from phase0.verifier import LocalizerV2
from tests.test_pipeline_v2 import FunctionVerifier, _fpipeline, _ftask

SPECS = (ArmSpec("control", None), ArmSpec("treatment", "rolling", 0.0), ArmSpec("ungated", "rolling", 0.0))


def test_warmup_not_scored_and_memory_is_as_of_previous_task():
    tasks = [_ftask(i) for i in range(1, 9)]
    p, truth = _fpipeline(tasks)
    arms = p.rolling(tasks, warmup=0, seed=1, specs=SPECS)
    c, t = arms["control"], arms["treatment"]
    assert len(c.flags_by_task) == 8 and len(t.flags_by_task) == 8
    # promotion needs 2 bad records from 2 tasks: after task 2's tick -> visible from task 3 on
    ids = [x.instance_id for x in tasks]
    assert t.version_by_task[ids[0]] is None and t.version_by_task[ids[1]] is None
    assert t.flags_by_task[ids[0]] == c.flags_by_task[ids[0]] and t.flags_by_task[ids[1]] == c.flags_by_task[ids[1]]   # no memory yet: identical to control
    assert all(t.version_by_task[i] is not None for i in ids[2:])
    assert all(len(t.flags_by_task[i]) == 1 for i in ids[2:]) and all(len(c.flags_by_task[i]) == 2 for i in ids)       # memory removed the wrong flag
    assert all(c.version_by_task[i] is None for i in ids)
    # with a warm-up, the first tasks are learned from but never scored
    p2, _ = _fpipeline(tasks)
    arms2 = p2.rolling(tasks, warmup=3, seed=1, specs=SPECS)
    assert set(arms2["control"].flags_by_task) == set(ids[3:]) and p2.gate3_stats()["n_warmup"] == 3
    assert p2.kernel.frozen and p2.frozen_version


def test_learning_stream_is_the_control_arm_only():
    tasks = [_ftask(i) for i in range(1, 7)]
    p, _ = _fpipeline(tasks)
    p.rolling(tasks, warmup=0, seed=2, specs=SPECS)
    ingests = p.kernel.ledger.events("ingest")
    assert len(ingests) == 12                      # 6 tasks x 2 control flags; the treatment's single flag is never ingested
    assert p.gate3_stats()["promoted"] == 1


def test_failed_task_is_dropped_from_every_arm_but_still_learned_from_when_control_succeeded():
    class TreatmentOnlyFlaky(FunctionVerifier):
        def complete(self, req):
            if "issue 4" in req.user and "Relevant memory" in req.user:
                raise RuntimeError("boom in treatment")
            return super().complete(req)
    tasks = [_ftask(i) for i in range(1, 7)]
    p, _ = _fpipeline(tasks)
    p.localizer = LocalizerV2(TreatmentOnlyFlaky(), "m", k=2)
    arms = p.rolling(tasks, warmup=0, seed=3, specs=SPECS)
    for a in arms.values():
        assert "o__r-4" in a.errors and "o__r-4" not in a.flags_by_task and len(a.flags_by_task) == 5
    assert "o__r-4" not in p.learn_errors and len(p.kernel.ledger.events("ingest")) == 12     # control succeeded: learned from

    class ControlFlaky(FunctionVerifier):
        def complete(self, req):
            if "issue 4" in req.user and "Relevant memory" not in req.user:
                raise RuntimeError("boom in control")
            return super().complete(req)
    p2, _ = _fpipeline(tasks)
    p2.localizer = LocalizerV2(ControlFlaky(), "m", k=2)
    arms2 = p2.rolling(tasks, warmup=0, seed=3, specs=SPECS)
    assert "o__r-4" in p2.learn_errors and all("o__r-4" in a.errors for a in arms2.values())


def test_negative_control_learns_nothing_and_arms_are_identical():
    tasks = [_ftask(i) for i in range(1, 7)]
    p, _ = _fpipeline(tasks)
    arms = p.rolling(tasks, warmup=2, seed=4, specs=SPECS, learn=False)
    assert p.gate3_stats()["promoted"] == 0 and p.gate3_stats()["candidate_writes"] == 0
    assert arms["treatment"].flags_by_task == arms["control"].flags_by_task == arms["ungated"].flags_by_task
    assert all(v is None for v in arms["treatment"].version_by_task.values())


def test_circuit_breaker_stops_a_dead_endpoint():
    class Dead(FunctionVerifier):
        def complete(self, req):
            raise RuntimeError("HTTP 403 key limit exceeded")
    import pytest
    tasks = [_ftask(i) for i in range(1, 15)]
    p, _ = _fpipeline(tasks)
    p.localizer = LocalizerV2(Dead(), "m", k=2)
    with pytest.raises(RuntimeError, match="consecutive task failures"):
        p.rolling(tasks, warmup=0, seed=1, specs=SPECS, max_consecutive_failures=3)
