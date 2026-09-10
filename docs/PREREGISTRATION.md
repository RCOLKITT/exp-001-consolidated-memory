# EXP-001 Pre-registration

**Status:** UNFILLED. Fill and publish (commit + tag `prereg-v1`, and post the
commit hash somewhere timestamped and public) before Gate 2 exits. After
that, changing any value below invalidates the result.

| Item | Value |
|---|---|
| Repositories (full list) | draft (run 7 gate; ceiling rule pending, D19): conan-io/conan, aws-cloudformation/cfn-lint, matplotlib/matplotlib, deepset-ai/haystack, pylint-dev/pylint, instructlab/instructlab, keras-team/keras, reflex-dev/reflex, streamlink/streamlink, sphinx-doc/sphinx, pdm-project/pdm, sissbruecker/linkding, pvlib/pvlib-python |
| Negative-control repo | draft: one of the 13 with a mid-length chain (e.g. streamlink/streamlink, 41) - owner to pick before publishing |
| Model + stated training cutoff | draft (D16): Llama 3.3 70B Instruct, "data freshness December 2023" (Meta model card) -> gate 2023-12-31; OpenRouter `meta-llama/llama-3.3-70b-instruct`, served by Crusoe bf16 then CoreWeave fp16, no other providers (D17, D19); fallback Llama 4 Maverick, "knowledge cutoff August 2024" -> gate 2024-08-31 |
| Embedding model + version (similarity seam) | |
| Chain split point per repo | draft: first 20 tasks build, rest evaluate (chronological) - revisit after the power calc with the Gate 0 rate |
| Θ_surprise | 0.35 (spec default; confirm) |
| Promotion thresholds | occurrences ≥ 3, distinct inputs ≥ 3, label = bad only, SoD on, cluster_similarity = ____ |
| TTL (in nightly runs) | |
| Minimum promoted memories per repo (Gate 3 floor) | |
| Minimum detectable effect (from power calc) | draft: p0 = 0.673 (run 18); MDE ≈ 7.4 pts at ~588 eval tasks (13 repos), 15-pt lift needs 131/arm |
| Localization lift kill number | ≥ 15 pts absolute (MDE ≈ 7.4 pts, so 15 stands) |
| False-positive ceiling | ≤ +5 pts absolute |
| Hard stop date | |

## Sign-off
- Published at (UTC): ______
- Commit: ______
- Public timestamp (URL): ______
