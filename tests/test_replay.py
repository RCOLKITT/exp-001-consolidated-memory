"""Mechanism assertion: same input hash + same memory version => identical
output, every time. Wall clock differences never change the outcome."""
import random

from memkernel import Kernel, KernelConfig, PromotionPolicy
from memkernel.replay import compare, replay
from memkernel.seams import PassthroughOracle, TokenJaccardSimilarity
from memkernel.synthetic import StreamSpec, generate
from tests.conftest import fixed_clock


def _factory(clock):
    cfg = KernelConfig(ttl_ticks=20, policy=PromotionPolicy(schedule_every_ticks=4, cluster_similarity=0.6))
    return lambda: Kernel(cfg, TokenJaccardSimilarity(), PassthroughOracle(), clock=clock)


def _run(k: Kernel, records):
    for i, r in enumerate(records):
        k.ingest(r)
        if i % 3 == 2:
            k.tick()
    k.snapshot()
    for r in records[:10]:
        k.ingest(r.__class__(**{**r.__dict__, "id": r.id + "-b"}))
    if k.store.live():
        k.supersede(k.store.live()[0].id, k.store.live()[0].content + " revised", note="test")
    k.freeze()
    return k


def test_replay_is_byte_identical():
    records = generate(StreamSpec(n_records=120, n_patterns=40, redundant_fraction=0.5, seed=3))
    a = _run(_factory(fixed_clock())(), records)
    assert len(a.store) > 0, "stream must promote something for the test to be meaningful"
    b = replay(a.trace, _factory(fixed_clock()))
    rep = compare(a, b)
    assert rep.identical, rep
    assert a.ledger.head_hash() == b.ledger.head_hash()
    assert a.ledger.verify() == (True, None)


def test_wall_clock_jitter_does_not_change_outcome():
    records = generate(StreamSpec(n_records=60, n_patterns=20, redundant_fraction=0.5, seed=5))
    rng = random.Random(11)
    jittery = lambda: 1_700_000_000.0 + rng.random() * 1e6
    a = _run(_factory(fixed_clock())(), records)
    b = replay(a.trace, _factory(jittery))
    assert compare(a, b).identical


def test_pinned_version_controls_visible_memory():
    records = generate(StreamSpec(n_records=60, n_patterns=20, redundant_fraction=0.5, seed=5))
    k = _run(_factory(fixed_clock())(), records)
    v = k.pinned_version
    assert k.store.at(v)
    k.pin(None)
    assert k.retrieve("anything") == ()          # control arm sees nothing
    k.pin(v)
    assert k.retrieve(k.store.at(v)[0].content)[0][1] == 1.0
