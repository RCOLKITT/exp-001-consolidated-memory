"""Similarity seam for the code adapter: embedding cosine over defect-pattern text.

Phase 2 fills `embed`. Requirements (Gate 1 determinism carries into Phase 4):
- pinned embedding model + version, recorded in the pre-registration block
- vectors cached by sha256(content) so a re-run never re-embeds differently
- no network call at similarity time during evaluation runs
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

from memkernel.canon import digest


class EmbeddingCosineSimilarity:
    def __init__(self, embed: Callable[[str], Sequence[float]]) -> None:
        self._embed = embed
        self._cache: dict[str, tuple[float, ...]] = {}

    def vector(self, text: str) -> tuple[float, ...]:
        key = digest(text)
        v = self._cache.get(key)
        if v is None:
            v = tuple(float(x) for x in self._embed(text))
            self._cache[key] = v
        return v

    def sim(self, a: str, b: str) -> float:
        va, vb = self.vector(a), self.vector(b)
        dot = sum(x * y for x, y in zip(va, vb))
        na, nb = math.sqrt(sum(x * x for x in va)), math.sqrt(sum(y * y for y in vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        # clamp cosine into the [0,1] contract
        return max(0.0, min(1.0, dot / (na * nb)))
