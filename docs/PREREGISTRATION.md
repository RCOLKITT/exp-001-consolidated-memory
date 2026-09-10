# EXP-001 Pre-registration

**Status:** UNFILLED. Fill and publish (commit + tag `prereg-v1`, and post the
commit hash somewhere timestamped and public) before Gate 2 exits. After
that, changing any value below invalidates the result.

| Item | Value |
|---|---|
| Repositories (full list) | draft (run 7 gate; ceiling rule pending, D19): conan-io/conan, aws-cloudformation/cfn-lint, matplotlib/matplotlib, deepset-ai/haystack, pylint-dev/pylint, instructlab/instructlab, keras-team/keras, reflex-dev/reflex, streamlink/streamlink, sphinx-doc/sphinx, pdm-project/pdm, sissbruecker/linkding, pvlib/pvlib-python |
| Negative-control repo | draft: one of the 13 with a mid-length chain (e.g. streamlink/streamlink, 41) - owner to pick before publishing |
| Model + stated training cutoff | draft (D16): Llama 3.3 70B Instruct, "data freshness December 2023" (Meta model card) -> gate 2023-12-31; OpenRouter `meta-llama/llama-3.3-70b-instruct`, served by Crusoe bf16 then CoreWeave fp16, no other providers (D17, D19); fallback Llama 4 Maverick, "knowledge cutoff August 2024" -> gate 2024-08-31 |
| Embedding model + version (similarity seam) | draft: sentence-transformers/all-MiniLM-L6-v2 @ 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 (D20) |
| Chain split point per repo | draft: 50 (conan, cfn-lint, matplotlib, haystack), 40 (pylint), 30 (instructlab, keras, reflex, streamlink, sphinx), 20 (pdm, linkding, pvlib); chronological |
| Θ_surprise | draft 0.45 (D23) |
| Promotion thresholds | draft: occurrences ≥ 2, distinct inputs ≥ 2 (findings §11.1; spec §6 said 3 — changed on Phase 0 evidence, before registration), label = bad only, SoD on; consolidation by file (D24); retrieval by MiniLM cosine |
| TTL (in nightly runs) | |
| Minimum promoted memories per repo (Gate 3 floor) | |
| Minimum detectable effect (from power calc) | draft: p0 = 0.673 (run 18); MDE ≈ 10.5 pts at ~300 eval tasks (recommended split) |
| Localization lift kill number | draft: ≥ 10 pts absolute (MDE ≈ 10.5 at ~300 eval tasks; ceiling ≈ 15 at promotion ≥ 2) — was 15 in the spec; revised on Phase 0 evidence before registration |
| False-positive ceiling | ≤ +5 pts absolute |
| Hard stop date | |

## Sign-off
- Published at (UTC): ______
- Commit: ______
- Public timestamp (URL): ______
