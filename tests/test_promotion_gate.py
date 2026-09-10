"""Mechanism assertion: promotion fires exactly at threshold, never earlier;
policy rules (§6) each block promotion independently."""
from memkernel import PromotionPolicy
from memkernel.records import MemoryObject
from memkernel.synthetic import make_record

# Records of the same pattern with distinct noise are REDUNDANT at the default
# theta (Jaccard >= 10/12), so the surprise gate reinforces the first buffered
# entry rather than adding new ones. Promotion counts supporting records, so
# the threshold is reached through reinforcement — the intended path.


def _kernel(make_kernel, **policy_over):
    policy = PromotionPolicy(cluster_similarity=0.6, schedule_every_ticks=1, **policy_over)
    return make_kernel(policy=policy, ttl_ticks=1000)


def _rec(i, **kw):
    return make_record(1, i, noise=(f"u{i}",), **kw)


def test_fires_exactly_at_threshold(make_kernel):
    k = _kernel(make_kernel)
    assert k.ingest(_rec(0, agent_id="a")).outcome == "buffered"
    assert k.ingest(_rec(1, agent_id="b")).outcome == "reinforced"
    assert len(k.buffer) == 1 and k.buffer.entries()[0].occurrences == 2
    assert k.tick().promotion.promoted == ()          # 2 < 3: never earlier
    assert k.ingest(_rec(2, agent_id="c")).outcome == "reinforced"
    res = k.tick().promotion
    assert len(res.promoted) == 1                     # exactly at 3
    m = res.promoted[0]
    assert len(m.provenance) == 3 and len(m.input_hashes) == 3
    assert m.approved_by == "promotion-gate" and "promotion-gate" not in m.proposed_by
    assert len(k.buffer) == 0                         # consumed
    assert k.store.live()[0].id == m.id


def test_only_bad_labels_count(make_kernel):
    k = _kernel(make_kernel)
    k.ingest(_rec(0, label="bad"))
    k.ingest(_rec(1, label="bad"))
    k.ingest(_rec(2, label="good"))     # a false positive must never teach the verifier
    k.ingest(_rec(3, label="unknown"))
    res = k.tick().promotion
    assert res.promoted == ()
    assert any("occurrences 2" in r.reason for r in res.rejected)


def test_requires_distinct_input_hashes(make_kernel):
    k = _kernel(make_kernel)
    for i in range(3):
        k.ingest(_rec(i, input_hash="same-artifact"))
    res = k.tick().promotion
    assert res.promoted == ()
    assert any("distinct_inputs 1" in r.reason for r in res.rejected)


def test_separation_of_duties(make_kernel):
    k = _kernel(make_kernel)
    for i in range(3):
        k.ingest(_rec(i, agent_id="promotion-gate"))  # proposer == approver
    res = k.tick().promotion
    assert res.promoted == ()
    assert any("separation_of_duties" in r.reason for r in res.rejected)


def test_contradiction_blocks(make_kernel):
    class AlwaysContradicts:
        def contradicted(self, content, memory):
            return tuple(m.id for m in memory) or ("phantom",)

    k = _kernel(make_kernel)
    k.promotion_gate.contradiction = AlwaysContradicts()
    for i in range(3):
        k.ingest(_rec(i))
    res = k.tick().promotion
    assert res.promoted == ()
    assert any(r.reason.startswith("contradicts") for r in res.rejected)


def test_promotion_runs_on_schedule_not_continuously(make_kernel):
    policy = PromotionPolicy(cluster_similarity=0.6, schedule_every_ticks=5)
    k = make_kernel(policy=policy, ttl_ticks=1000)
    for i in range(3):
        k.ingest(_rec(i))
    for t in range(1, 5):
        assert k.tick().promotion is None
    assert len(k.store) == 0
    assert k.tick().promotion is not None            # tick 5
    assert len(k.store) == 1


def test_promotion_disabled_after_freeze(make_kernel):
    import pytest
    from memkernel.kernel import KernelError

    k = _kernel(make_kernel)
    k.freeze()
    with pytest.raises(KernelError):
        k.promote()
    assert k.tick().promotion is None


def test_reinforce_threshold_discards_ambiguous_neighbours(make_kernel):
    """D22: with rho above 1-theta, a near-but-not-same candidate is discarded instead of merged."""
    from memkernel import KernelConfig, PromotionPolicy
    from memkernel.seams import PassthroughOracle, TokenJaccardSimilarity
    from memkernel import Kernel
    from memkernel.kernel import counting_clock
    from memkernel.synthetic import make_record
    cfg = KernelConfig(theta_surprise=0.6, reinforce_min_sim=0.9, ttl_ticks=100, policy=PromotionPolicy(schedule_every_ticks=1, cluster_similarity=0.5))
    k = Kernel(cfg, TokenJaccardSimilarity(), PassthroughOracle(), clock=counting_clock())
    assert k.ingest(make_record(1, 0)).outcome == "buffered"
    assert k.ingest(make_record(1, 1)).outcome == "reinforced"                    # identical content: sim 1.0
    assert k.ingest(make_record(1, 2, noise=("z1", "z2", "z3"))).outcome == "discarded"   # sim 10/13 = 0.77 < 0.9, surprise 0.23 < 0.6
    assert k.buffer.entries()[0].occurrences == 2
