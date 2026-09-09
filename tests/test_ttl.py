"""Mechanism assertion: TTL removes unpromoted entries; forgetting is default."""
from memkernel.synthetic import StreamSpec, generate


def test_ttl_expires_unpromoted(make_kernel):
    records = generate(StreamSpec(n_records=10, n_patterns=10, redundant_fraction=0.0))
    k = make_kernel(ttl_ticks=3)
    for r in records:
        k.ingest(r)
    assert len(k.buffer) == 10
    k.tick(); k.tick()
    assert len(k.buffer) == 10
    k.tick()                       # 3 ticks elapsed >= ttl
    assert len(k.buffer) == 0
    expired = k.ledger.events("expire")
    assert len(expired) == 1 and len(expired[0].payload["record_ids"]) == 10


def test_expired_record_becomes_surprising_again(make_kernel):
    records = generate(StreamSpec(n_records=1, n_patterns=1, redundant_fraction=0.0))
    r = records[0]
    k = make_kernel(ttl_ticks=2)
    assert k.ingest(r).decision.admitted
    k.tick(); k.tick()
    # same content, new record id: kernel has forgotten it
    r2 = r.__class__(**{**r.__dict__, "id": r.id + "-again"})
    assert k.ingest(r2).decision.admitted
