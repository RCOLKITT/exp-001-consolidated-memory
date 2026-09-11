"""Similarity seam for the code adapter: embedding cosine over defect-pattern text.

Three implementations behind one interface (sim(a, b) -> [0, 1]):
  - TokenJaccardSimilarity (memkernel.seams)      Phase 1 placeholder
  - HashingEmbedder + EmbeddingCosineSimilarity   dependency-free feature-hashing
                                                  vectors; deterministic anywhere;
                                                  used by tests and the tuning sweep
  - SentenceTransformerEmbedder + …               pinned model + revision; the
                                                  pre-registered seam for Phases 3–4

Determinism (Gate 1 carries into Phase 4): vectors are cached by
sha256(content) in a JSONL file that is saved with the run, so a replay
never re-embeds and never depends on the model being reachable.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Callable, Optional, Sequence

from memkernel.canon import digest

try:  # optional acceleration; results identical to the pure-Python path within float rounding
    import numpy as _np  # type: ignore
except ImportError:  # pragma: no cover
    _np = None

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]")


class HashingEmbedder:
    """Feature-hashing bag of unigrams + bigrams, L2-normalised. No model, no
    network, identical on every machine. Good enough to exercise the seam and
    to tune thresholds; not the pre-registered similarity."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"

    def __call__(self, text: str) -> list[float]:
        toks = [t.lower() for t in _TOKEN.findall(text)]
        feats = toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]
        v = [0.0] * self.dim
        for f in feats:
            h = int(hashlib.blake2b(f.encode(), digest_size=8).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 63) else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class SentenceTransformerEmbedder:
    """Pinned sentence-transformers model. Loaded lazily so importing the
    adapter never needs torch. `revision` is a git commit on the Hub — record
    it in the pre-registration block."""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2", revision: Optional[str] = None) -> None:
        self.model_name = model
        self.revision = revision
        self.name = f"{model}@{revision or 'unpinned'}"
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(self.model_name, revision=self.revision, device="cpu")
        return self._model

    def __call__(self, text: str) -> list[float]:
        v = self._load().encode([text], normalize_embeddings=True, convert_to_numpy=True)[0]
        return [float(x) for x in v]


class EmbeddingCosineSimilarity:
    def __init__(self, embed: Callable[[str], Sequence[float]], cache_path: Optional[str | Path] = None) -> None:
        self._embed = embed
        self.name = getattr(embed, "name", type(embed).__name__)
        self._cache: dict[str, tuple[float, ...]] = {}
        self._path = Path(cache_path) if cache_path else None
        self.hits = 0
        self.misses = 0
        if self._path and self._path.exists():
            for line in self._path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._cache[row["key"]] = tuple(row["vector"])

    def vector(self, text: str) -> tuple[float, ...]:
        key = digest({"embedder": self.name, "text": text})
        v = self._cache.get(key)
        if v is None:
            self.misses += 1
            v = tuple(float(x) for x in self._embed(text))
            self._cache[key] = v
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a") as f:
                    f.write(json.dumps({"key": key, "vector": list(v)}) + "\n")
        else:
            self.hits += 1
        return v

    def sim(self, a: str, b: str) -> float:
        va, vb = self.vector(a), self.vector(b)
        if _np is not None:
            xa, xb = _np.asarray(va), _np.asarray(vb)
            na, nb = float(_np.linalg.norm(xa)), float(_np.linalg.norm(xb))
            if na == 0.0 or nb == 0.0:
                return 0.0
            return max(0.0, min(1.0, float(xa @ xb) / (na * nb)))
        dot = sum(x * y for x, y in zip(va, vb))
        na, nb = math.sqrt(sum(x * x for x in va)), math.sqrt(sum(y * y for y in vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        # clamp cosine into the [0,1] contract (negative cosine = "no similarity")
        return max(0.0, min(1.0, dot / (na * nb)))


def make_similarity(kind: str, cache_path: Optional[str | Path] = None, model: Optional[str] = None, revision: Optional[str] = None):
    if kind == "jaccard":
        from memkernel.seams import TokenJaccardSimilarity
        return TokenJaccardSimilarity()
    if kind == "hashing":
        return EmbeddingCosineSimilarity(HashingEmbedder(), cache_path)
    if kind == "embedding":
        return EmbeddingCosineSimilarity(SentenceTransformerEmbedder(model or "sentence-transformers/all-MiniLM-L6-v2", revision), cache_path)
    raise ValueError(f"unknown similarity kind {kind!r}")


_LOC = re.compile(r"=> (.+?) ::")


def location_of(content: str) -> str:
    """The location part of a code-adapter record (`symptom => path :: reason`)."""
    m = _LOC.search(content)
    return m.group(1).strip() if m else ""


class FileKeyedSimilarity:
    """Consolidation seam for the code adapter (D24): two records are the same
    pattern iff they point at the same file. sim = 1.0 for the same file, else
    0.0, so the surprise gate admits each new file once, every repeat of a
    file reinforces it, and promotion clusters never mix files (purity 1.0 by
    construction). Records without a location fall back to `inner`."""

    def __init__(self, inner=None) -> None:
        self.inner = inner
        self.name = "file-keyed" + (f"+{getattr(inner, 'name', type(inner).__name__)}" if inner else "")

    def sim(self, a: str, b: str) -> float:
        la, lb = location_of(a), location_of(b)
        if la and lb:
            return 1.0 if la == lb else 0.0
        return self.inner.sim(a, b) if self.inner else 0.0


class FunctionKeyedSimilarity(FileKeyedSimilarity):
    """v2 consolidation seam: two records are the same pattern iff they point
    at the same `(path, qualname)`. The location part of a function-level
    record is `path tokens # qualname` (adapters.code.pipeline.record_content),
    so equality on the location string is equality on the pair; a record with
    no `#` (file-level) keys on its file, as in v1."""

    def __init__(self, inner=None) -> None:
        super().__init__(inner)
        self.name = "function-keyed" + (f"+{getattr(inner, 'name', type(inner).__name__)}" if inner else "")
