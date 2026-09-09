"""Mechanism assertion: the surprise gate discards the injected redundant
fraction within tolerance."""
import pytest

from memkernel.synthetic import StreamSpec, expected_redundant, generate


@pytest.mark.parametrize("redundant", [0.3, 0.6, 0.7, 0.85])
def test_discards_injected_redundant_fraction(make_kernel, redundant):
    spec = StreamSpec(n_records=200, n_patterns=200, redundant_fraction=redundant, seed=7)
    records = generate(spec)
    k = make_kernel(ttl_ticks=10_000)  # TTL longer than the stream: no forgetting here
    discarded = 0
    for r in records:
        if not k.ingest(r).decision.admitted:
            discarded += 1
    injected = expected_redundant(records)
    assert injected == pytest.approx(len(records) * redundant, abs=1)
    # exact match expected: same-pattern Jaccard >= 10/14 > 1-theta, cross-pattern <= 4/24
    assert discarded == injected
    assert discarded / len(records) == pytest.approx(redundant, abs=0.02)


def test_first_occurrence_always_admitted(make_kernel):
    records = generate(StreamSpec(n_records=50, n_patterns=50, redundant_fraction=0.0, seed=1))
    k = make_kernel()
    assert all(k.ingest(r).decision.admitted for r in records)
    assert len(k.buffer) == 50


def test_surprise_written_to_ledger(make_kernel):
    records = generate(StreamSpec(n_records=5, n_patterns=5, redundant_fraction=0.0))
    k = make_kernel()
    for r in records:
        k.ingest(r)
    ingests = k.ledger.events("ingest")
    assert len(ingests) == 5
    assert all("surprise" in e.payload["decision"].to_canonical() for e in ingests)
    assert k.ledger.verify() == (True, None)
