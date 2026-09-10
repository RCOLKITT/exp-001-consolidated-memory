"""The similarity seam with real vectors: hashing embedder everywhere, the
pinned sentence-transformers model only where it is installed."""
import pytest

from adapters.code.similarity import EmbeddingCosineSimilarity, HashingEmbedder, make_similarity
from memkernel.synthetic import StreamSpec, expected_redundant, generate
from phase2.tune import recommend, sweep


def test_hashing_cosine_contract_and_cache(tmp_path):
    s = EmbeddingCosineSimilarity(HashingEmbedder(), tmp_path / "vec.jsonl")
    assert s.sim("parser drops last row", "parser drops last row") == pytest.approx(1.0)
    assert 0.0 <= s.sim("parser drops last row", "docker build fails on arm64") < 0.3
    assert s.sim("", "x") == 0.0
    assert s.misses == 4 and s.hits >= 1
    s2 = EmbeddingCosineSimilarity(HashingEmbedder(), tmp_path / "vec.jsonl")   # persisted vectors
    assert s2.sim("parser drops last row", "docker build fails on arm64") == s.sim("parser drops last row", "docker build fails on arm64")
    assert s2.misses == 0


def test_sweep_finds_a_working_threshold_for_hashing():
    """Gate 1's discard assertion, for the hashing seam, at a tuned Θ (D14)."""
    sim = make_similarity("hashing")
    spec = StreamSpec(n_records=150, n_patterns=150, redundant_fraction=0.6, seed=3)
    rows = sweep(sim, [0.2, 0.3, 0.4, 0.5, 0.6], [0.5, 0.6, 0.7], spec)
    rec = recommend(rows, tol=0.05)
    assert rec is not None, rows
    assert abs(rec["discard_rate"] - 0.6) <= 0.05 and rec["purity"] == 1.0 and rec["promoted"] > 0


def test_make_similarity_kinds():
    assert make_similarity("jaccard").sim("a b", "a b") == 1.0
    assert make_similarity("hashing").name == "hashing-512"
    with pytest.raises(ValueError):
        make_similarity("nope")


@pytest.mark.skipif(pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed") is None, reason="no model")
def test_pinned_embedding_model_if_available(tmp_path):
    sim = make_similarity("embedding", tmp_path / "vec.jsonl")
    try:
        a = sim.sim("parser drops the last row of a CSV", "CSV parser loses final line")
    except Exception as e:  # offline runner
        pytest.skip(f"model not loadable here: {e}")
    b = sim.sim("parser drops the last row of a CSV", "docker build fails on arm64")
    assert a > b
