# EXP-001 Pre-registration — v2 (function-level memory, prequential evaluation)

**Status:** REGISTERED 2026-09-11 at the commit that adds this file, the tip of branch
`prereg/v2`; the owner creates tag `prereg-v2` on that commit. Owner
decisions on record: design A (rolling evaluation), primary arm ungated
(option 2 of draft §14), placebo arm included ("option 2 with the placebo
arm, tag it and run"). Changing any value below after the tag invalidates
the result. The draft that led here, with every intermediate number, is
`docs/PREREGISTRATION-v2-DRAFT.md`; v1 (`prereg-v1`) stands untouched.

## Hypothesis

**H2.** With the verifier, corpus and repositories of v1, a per-repository
kernel that consolidates function-level defect memories
(`symptom => path # qualname :: reason`) and injects the top-k retrieved
memories into the verifier's prompt raises task-level **function-level
hit@3** by at least the kill number over a paired control on the same
tasks, without raising the function-level false-positive rate by more than
5 points, with no lift on a negative-control repository, and by more than a
placebo arm that injects the same number of irrelevant memory lines.

## Values

| Item | Value | Source |
|---|---|---|
| Corpus, freshness gate, verifier, serving, providers, `served_by` rule | as v1: SWE-bench-Live Python `full` (phase0 run 18 artifact), gate 2023-12-31, Llama 3.3 70B via OpenRouter Crusoe→CoreWeave, no fallbacks | v1 |
| Verifier prompt | two-stage (`LocalizerV2`): stage 1 = v1 file prompt, unchanged; stage 2 = function index of the stage-1 files, ≤ 3 `path::qualname` flags; k = 3, temperature 0; treatment differs from control only by the memory section, present in both stages | draft §3 |
| Metric (primary) | task-level function-level hit@3: a flagged `path::qualname` whose span overlaps a non-test **Python-source** gold hunk of the same symbol; a task with no Python gold hunk is outside the metric | draft §4, §11 |
| Metric (paired) | flag-level false-positive rate at k = 3, same flags | v1 D18 |
| Secondary metrics | file-level hit@3 from the stage-1 flags; paired CIs; per-repo table | draft §4 |
| Embedding (retrieval) | sentence-transformers/all-MiniLM-L6-v2 @ `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | v1 D20 |
| Consolidation | function-keyed: same `(path, qualname)` ⇒ same pattern | draft §3 |
| Promotion / TTL / Θ / ρ | ≥ 2 `bad` records from ≥ 2 tasks; TTL 30; Θ 0.45, ρ 0.70, cluster 0.60 (inert under keyed consolidation) | v1 |
| Evaluation | **prequential**: tasks in chain order per repo; first **20** are warm-up (learned from, never scored); every later task is scored by every arm against the snapshot pinned after the previous task | draft §12–13, D34 |
| Learning stream | the control arm's flags on every task; the placebo and memory arms never feed memory | draft §3 |
| Arms | `control` (no memory) · **`treatment`** (memory, τ = 0, top-k = 3; **primary**) · `gated` (memory, τ = 0.50; secondary, attribution of gating) · `placebo` (as many lines as `treatment` injects on that task, drawn by the same retrieval similarity from the placebo pool); arm order shuffled per task, **seed 11** | draft §14 option 2 |
| Placebo pool | promoted memories of streamlink/streamlink and pvlib/pvlib-python from experiment run 8 (repositories outside the experiment); file `docs/placebo-pool.v2.json`, **n = 5, sha256 `6c717cf770566ec9a6f6e2f5b4d63793bef142202c251aa2dfdd28f6eb2749c8`** | run 9 |
| τ (gated arm) | 0.50 — registered fallback rule on run 8 (0/72 retrievals named a gold symbol; 90th percentile of non-matching cosines) | draft §14 |
| Treatment repos | conan-io/conan, aws-cloudformation/cfn-lint, matplotlib/matplotlib, deepset-ai/haystack, pylint-dev/pylint, instructlab/instructlab, keras-team/keras, reflex-dev/reflex, sphinx-doc/sphinx, pdm-project/pdm | v1 |
| Negative control | sissbruecker/linkding — rolling with learning off, all arms scored | v1 |
| Eval pool | **530** scorable tasks (run 26) | `docs/v2-fill-designA.json` |
| p0 (function level) | **0.442** eval-weighted (run 24) | draft §13 |
| Ceiling | **15.6 pts** | draft §12 |
| MDE (unpaired two-proportion) | **8.6 pts** | `phase2.power.mde_at` |
| **Kill number** | **9 pts** absolute, `treatment` vs `control`, aggregate over the 10 treatment repos | ceil(max(MDE, 0.5 × ceiling)) |
| **Placebo criterion** | `treatment` − `placebo` ≥ **4.5 pts** (half the kill number), aggregate; reported with its paired CI | this block |
| False-positive ceiling | `treatment` FP rise ≤ 5 pts absolute | v1 |
| Majority criterion | lift > 0 in a majority of treatment repos (reported, as v1) | v1 |
| Negative-control criterion | lift = 0 within noise on linkding | v1 |
| Paired interval | paired Wald and bootstrap CIs are the primary intervals; assumed discordance for the paired MDE **0.30** (informational; the kill number does not depend on it) | draft §12 |
| Gate 3 floor (per treatment repo, chain end) | ≥ 2 promoted memories; discard rate ≥ 0.5 × whole-chain repeat share: conan 0.106, cfn-lint 0.141, matplotlib 0.070, haystack 0.141, pylint 0.097, instructlab 0.200, keras 0.023, reflex 0.092, sphinx 0.058, pdm 0.114. Failing repos stay in the primary analysis (D28) | run 25 |
| Sharding | the run may be split by repository into shards A/B/C (`docs/exp-run.v2.json`); each shard's config equals the registered file except `repos`; results are merged by `phase4.aggregate`, which refuses a repo in two shards. Sharding is exact: one kernel and one chain per repo | this block |
| Error handling | a task failing in any arm is excluded from every arm; counts reported; > 5% excluded in any repo is reported as a caveat | draft §3 |
| Hard stop | **2026-10-23** (six weeks) | v1 §10 |

## Analysis plan (fixed)

Primary: `treatment` vs `control`, aggregate function-level lift over the
10 treatment repos against the kill number (9), with FP rise ≤ 5, negative
control at 0, and `treatment` − `placebo` ≥ 4.5. All four must hold for H2
to be supported; any failing one kills it. Everything else — `gated` vs
`control`, `placebo` vs `control`, file-level secondary, per-repo table,
Gate 3 per repo, paired CIs — is reported, never substituted.

## Run configuration

`docs/exp-run.v2.json` is the registered `.exp-run.json`. A shard's
`config.json` must equal it byte for byte except the `repos` list, which
must equal one of its `shards`. The merge run's config lists the shard run
numbers.

## Sign-off
- Registered by: Claude (session), on the owner's instruction, 2026-09-11
- Registered commit: the commit adding this file = tip of branch `prereg/v2`; tag `prereg-v2` by the owner
- sha256 of `docs/exp-run.v2.json`: `6eade5982644b4f67618be027d8e1be90d0711f2a86d6f0d107a79fb3a491c21`
