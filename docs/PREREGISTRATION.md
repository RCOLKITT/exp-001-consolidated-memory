# EXP-001 Pre-registration — v1

**Status:** REGISTERED at tag `prereg-v1` (2026-09-10). Owner approved the
design and the ceiling rule ("yes go with your recommended design and
option b"). Changing any value below after this tag invalidates the result
(spec §7). The tag is the public timestamp; the owner may add an external
one (e.g. the tag's commit hash posted publicly) as a second witness.

## Values

| Item | Value | Source |
|---|---|---|
| Corpus | SWE-bench-Live/SWE-bench-Live (Python), `full` split, pulled by phase0 run 18 (artifact `corpus-18`; 1,888 tasks, 2021-07-22 → 2025-09-02) | findings §1 |
| Freshness gate | task `created_at` strictly after **2023-12-31**; undated tasks rejected; enforced at import (`phase0/freshness_gate.py`) | D15, D16 |
| Verifier model + stated cutoff | Llama 3.3 70B Instruct — Meta model card: "data freshness: December 2023" | D16 |
| Verifier serving | OpenRouter `meta-llama/llama-3.3-70b-instruct`, providers **Crusoe (bf16) then CoreWeave (fp16)**, `allow_fallbacks: false`; any request served elsewhere invalidates the run; `served_by` recorded per request | D17, D19 |
| Verifier prompt | `phase0/verifier.py` `SYSTEM_PROMPT` + `render_prompt`, k = 3, effort "high", temperature 0; treatment differs from control only by the memory section | D9 |
| Localization metric | task-level hit@3 at file level, non-test files; paired with flag-level false-positive rate at k = 3 (floor ≈ 0.67 noted) | D9, D18 |
| Embedding model (retrieval seam) | sentence-transformers/all-MiniLM-L6-v2 @ `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, vectors cached with each run | D20 |
| Consolidation seam | file-keyed: same file ⇒ same pattern; retrieval by embedding cosine of issue text vs memory content | D24 |
| Θ_surprise / ρ / cluster | 0.45 / 0.70 / 0.60 (govern the semantic variant and synthetic Gate 1 checks; inert under file-keyed consolidation) | D23 |
| Promotion | **≥ 2 `bad` records from ≥ 2 distinct tasks**; label = bad only; no unresolved contradiction; separation of duties (proposer `verifier:<model>`, approver `promotion-gate`) | §6, D25 |
| TTL | 30 ticks (one tick per task) | D4 |
| Memory scope | one kernel per repository; no cross-repo memory | §1 |
| Ceiling rule | repos with Phase 0 control hit@3 ≥ 0.90 (run 18, first 20 tasks) are excluded: **streamlink/streamlink (1.00), pvlib/pvlib-python (0.95)** | D19, findings §8 |
| Build split rule | chronological; build = 50 for chains ≥ 70 tasks, 40 for ≥ 58, 30 for ≥ 41, else 20; eval = the rest | findings §11.1 |
| Negative-control repo | **sissbruecker/linkding** (no memory-building run; both arms evaluated) | this block |
| Evaluation | both arms on every eval task, interleaved, task order seeded (**seed 7**); control pins `memory_version = None`, treatment pins the frozen version | Phase 4 |
| Control-arm rate (Phase 0) | 0.673 hit@3 over 260 tasks, 13 repos (run 18) | findings §8 |
| Treatment eval pool | **373 tasks** across 10 repos | table below |
| Minimum detectable effect | **≈ 9.2 pts** (two-proportion, α 0.05 two-sided, power 0.8, p0 0.673, n = 373) | `phase2.power` |
| Ceiling on lift (file-level, promote ≥ 2) | **≈ 17.9 pts** aggregate (seen2 × (1 − p0), run 21) | findings §10–11 |
| Localization lift kill number | **≥ 10 pts absolute** aggregate over treatment repos (spec said 15; revised on Phase 0 evidence before registration; never lowered after) | §7 |
| False-positive ceiling | rise ≤ 5 pts absolute (paired, same k) | Gate 4 |
| Majority criterion | lift > 0 in a majority of treatment repos; reported per repo against per-repo ceiling | Gate 4 |
| Negative-control criterion | lift = 0 within noise on linkding | Gate 4 |
| Gate 3 floor (file-keyed seam) | discard rate ≥ 0.40 per repo and ≥ 2 promoted memories per treatment repo; promoted memories legible on inspection | findings §12 |
| Hard stop date | 2026-10-22 (six weeks from registration) | §10 |

## Repositories

| repo | chain | build | eval | control hit@3 (Phase 0) | ceiling (pts, promote ≥ 2) | role |
|---|---:|---:|---:|---:|---:|---|
| conan-io/conan | 165 | 50 | 115 | 0.55 | 10.9 | treatment |
| aws-cloudformation/cfn-lint | 109 | 50 | 59 | 0.20 | 38.0 | treatment |
| matplotlib/matplotlib | 101 | 50 | 51 | 0.75 | 15.2 | treatment |
| deepset-ai/haystack | 88 | 50 | 38 | 0.80 | 6.8 | treatment |
| pylint-dev/pylint | 62 | 40 | 22 | 0.45 | 20.0 | treatment |
| instructlab/instructlab | 52 | 30 | 22 | 0.80 | 13.6 | treatment |
| keras-team/keras | 48 | 30 | 18 | 0.55 | 5.0 | treatment |
| reflex-dev/reflex | 44 | 30 | 14 | 0.65 | 25.0 | treatment |
| sphinx-doc/sphinx | 39 | 20 | 19 | 0.60 | 37.9 | treatment |
| pdm-project/pdm | 35 | 20 | 15 | 0.75 | 15.0 | treatment |
| sissbruecker/linkding | 34 | 20 | 14 | 0.70 | 23.6 | negative control |
| streamlink/streamlink | 41 | — | — | 1.00 | — | excluded (ceiling rule) |
| pvlib/pvlib-python | 30 | — | — | 0.95 | — | excluded (ceiling rule) |

## Run configuration

`docs/exp-run.prereg.json` is the exact `.exp-run.json` for the registered
run; `results/experiment/<n>/config.json` of the Phase 3–4 run must equal
it byte for byte.

## Gates that must pass before Phase 3 starts
- Gate 0.1 published baseline reference (D10) — owner to pin
- Gate 2.3 oracle hand-check ≥ 0.95 on `results/phase0/19/control/handcheck.csv` — owner to label

## Sign-off
- Registered by: Claude (session), on the owner's instruction, 2026-09-10
- Tag: `prereg-v1`
- External timestamp (optional): ______
