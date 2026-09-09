# Code adapter (GitHub / SWE-bench-Live)

Implements the three seams from spec §2 for the defect-localization domain.
Nothing here is wired until Phase 2 (Gate 0 and Gate 1 must pass first).

| Seam | File | Status |
|---|---|---|
| Outcome oracle | `oracle.py` | stub — location match vs. ground-truth patch |
| Similarity | `similarity.py` | stub — embedding cosine over defect-pattern text |
| Promotion policy | `policy.py` | **done** — §6 constants, hand-set |

Rules the adapter must respect:
- The oracle is programmatic. No human reads findings (§8, confirmation bias).
- `label = bad` means "the flagged location matches a ground-truth patch
  location". `good` means a flag with no match (a false positive). Only `bad`
  is promotion-eligible (§6.5, self-poisoning guard).
- Similarity must be deterministic: pin the embedding model and cache vectors
  by content hash so replay (Gate 1) holds end to end.
