# Phase 0 findings — corpus and freshness (2026-09-09)

Source of every number: `results/phase0/<run>/corpus-summary.json` and
`chain-report.md`, produced by `.github/workflows/phase0.yml` on a hosted
runner from the public Hugging Face datasets. Nothing here is from memory.

## 1. What the public corpora contain

| Corpus (run) | Tasks | Repos | Dates | Repos ≥ 20 tasks | Repos ≥ 40 | Median chain |
|---|---:|---:|---|---:|---:|---:|
| SWE-bench-Live/SWE-bench-Live `full`, Python (run 3) | 1,888 | 223 | 2021-07-22 → 2025-09-02 | 24 | 9 | 2 |
| SWE-bench-Live/MultiLang, all 8 language splits (run 4) | 1,077 | 431 | 2020-06-29 → 2026-07-31 | 7 | 0 | 1 |

The Python corpus is where the long chains are: conan (165), cfn-lint (109),
matplotlib (102), haystack (88), pylint (62), instructlab (52), keras (48),
reflex (44), streamlink (41), sphinx (39), pdm (35), linkding (34), pvlib (30).
Thirteen repos clear a 20-build / 10-eval split. That is the corpus the
experiment was designed for.

## 2. What the freshness gate does to it

Vendor-stated training data cutoffs (D15): Fable 5.1 Jun 2026, Opus 5 May
2026, Sonnet 5 Jan 2026, Haiku 4.5 Jul 2025.

Tasks surviving "created strictly after the cutoff":

| Cutoff | Python `full`: tasks / repos ≥ 20 | MultiLang: tasks / repos ≥ 20 |
|---|---|---|
| 2024-07-01 | 1,392 / 13 | 1,072 / 7 |
| 2025-01-01 | 905 / 6 | 1,071 / 7 |
| 2025-04-01 | 591 / 3 | 1,066 / 7 |
| 2025-07-01 (≈ Haiku 4.5) | 248 / 0 | 1,006 / 7 |
| 2026-01-01 (≈ Sonnet 5) | **0 / 0** | 663 / 5 |
| 2026-01-31 Sonnet 5, gated run 5 | — | **659 / 5** (227 repos; 1 repo ≥ 30: httrack 38; then duckdb 26, floci 23, langchain4j 23, codegraph 20) |
| 2026-05-31 Opus 5, gated run 6 | — | **309 / 2** (68 repos; httrack 38, duckdb 25; median chain 3) |

The Python corpus stopped growing after August 2025 (per-month counts:
2025-06: 109, 2025-07: 115, 2025-08: 137, 2025-09: 3), despite the README's
promise of 50 new tasks a month. MultiLang is what has been maintained
(2026-03: 142, 2026-04: 181, 2026-05: 22, 2026-06: 78, 2026-07: 231).

## 3. Consequence

**With any Claude 5 model, the Python corpus is unusable under the gate, and
the multi-language corpus has no repo with a chain long enough for the
split.** This is Gate 2's kill condition ("chains too short") showing up in
Phase 0, which is the cheap place to find it.

The experiment's constraints are: fresh tasks (§8 contamination), long
per-repo chains (memory needs something to accumulate), and a programmatic
oracle. The public data satisfies any two.

## 4. Options (decision for the owner, not made here)

| Option | Fresh? | Chains? | Cost | Notes |
|---|---|---|---|---|
| A. Model with a ≤ mid-2024 cutoff on the Python corpus | yes | **13 repos ≥ 20** | new `ModelClient` for that model | The corpus is rich for it: 1,392 fresh tasks. Choose the model to fit the gate, not the corpus to fit the model. Localization quality will be lower than Opus 5; the *lift* is what is measured, not the level. |
| B. Sonnet 5 on MultiLang 2026 tasks | yes | weak: 5 repos ≥ 20 (httrack 38, duckdb 26, floci 23, langchain4j 23, codegraph 20), 4 languages | per-language file trees in the adapter | Run 5. At a 12-build / 8-eval split, five repos and ~40 eval tasks total: far below the ~163 per arm the power calculation asks for at a 15-point MDE. |
| C. Opus 5 on MultiLang after May 2026 | yes | very weak: httrack 38, duckdb 25, then ≤ 17 | as B | Run 6. Fails Gate 2 on chain length. |
| D. Build fresh Python tasks from the 13 long-chain repos' post-2025-09 issues | yes | yes, by construction | weeks: the SWE-bench-Live curation pipeline + RepoLaunch + validation | Turns Phase 0 into a corpus-construction project. Also yields a publishable dataset. |
| E. Weaken the gate | — | — | — | **Not an option** (§8). A contaminated result is uninterpretable. |

Recommendation: **A** if a suitable model with a documented cutoff and
acceptable localization ability exists (verify its stated cutoff the same
way D15 was verified); otherwise **B** with a reduced repo list and the
power calculation re-run on the real chain lengths. **D** only if the
experiment is worth several extra weeks.

## 5. Not yet done in Phase 0
- Control-arm run and determinism check (needs the model choice above and
  the `ANTHROPIC_API_KEY` secret, or the option-A model's client).
- Published baseline reference number (D10).
- Docker images and time-machine pinning (deferred, D8).

## 6. Option A, measured (2026-09-10)

Owner chose option A. Candidate models with vendor-documented cutoffs were
gated against the Python corpus (runs 7, 9, 10; D16 has the sources).

| Gate (model) | Tasks | Repos >= 20 | Eligible at 20 build / 10 eval | Eval tasks available (build = 20) |
|---|---:|---:|---:|---:|
| 2023-12-31 (Llama 3.3 70B, "data freshness December 2023") | 1,884 | 24 | **13** - conan 165, cfn-lint 109, matplotlib 101, haystack 88, pylint 62, instructlab 52, keras 48, reflex 44, streamlink 41, sphinx 39, pdm 35, linkding 34, pvlib 30 | ~588 |
| 2024-08-31 (Llama 4 Maverick/Scout, "knowledge cutoff August 2024") | 1,215 | 10 | **4** - conan 83, haystack 67, cfn-lint 65, matplotlib 53 (then pylint 27, fastmcp 25, datamodel-code-generator 23, reflex 23, instructlab 22, streamlink 20) | ~188 |
| 2025-03-31 (Claude Sonnet 4 / Opus 4, cutoff unverified) | 595 | 3 | 2 - haystack 36, conan 33 | ~29 |

Both Llama gates clear the power floor (~163 eval tasks per arm at a
15-point MDE from a 55% baseline; arms share tasks). The Claude 4 gate does not.

**Recommendation: Llama 3.3 70B Instruct.** The design leans on per-repo
reporting, a majority-of-repos criterion, and a negative-control repo; 13
eligible repos make those meaningful, 4 make them fragile (one negative
control leaves three treatment repos). Llama 4 Maverick is the stronger
coder, but the experiment measures lift, not level, and a weaker verifier
with more room to improve is not a disadvantage for the efficacy claim.
If Gate 0's published-baseline comparison needs a stronger verifier, Llama 4
with the four long-chain repos is the fallback, pre-registered as such.

Hosting: any OpenAI-compatible provider serving the open weights
(`--provider openai-compatible`); pin the provider's exact model id and
quantisation in the pre-registration block, because different quantised
builds are different verifiers.

## 7. First control-arm run (run 17, 2026-09-10)

Verifier: Llama 3.3 70B Instruct via OpenRouter, pinned to Crusoe bf16
(every one of the 50 requests reports `served_by: Crusoe`). Corpus: Python
`full`, gate 2023-12-31, restricted to the 13 draft repos; the first 50
tasks by (repo, date) are all aws-cloudformation/cfn-lint. k = 3.

| Metric | Value |
|---|---|
| Tasks scored / attempted | 50 / 50 (0 errors, 0 truncated file lists; ~1,010 files each) |
| Localization rate (task hit@3, file level) | **0.34** |
| False-positive rate (flags with no gold overlap / flags) | 0.879 (141 flags, 124 FP) |
| Determinism: offline rerun vs original | **identical** (`compare.txt`, flags sha256 b2454e09…) |
| Wall time | 263 s for 50 tasks |

Two cautions. (1) One repo: cfn-lint issues map to rule files, a hard
target; this number is not the corpus rate. Run 18 samples every repo. (2)
At fixed k = 3 with mostly single-file gold patches the flag-level FP rate
has a floor near 0.67 even for a perfect verifier; it is meaningful only as
the paired difference between arms (Gate 4), never as a level (D18).

Gate 0 status after run 17: freshness gate ✓ (in code), determinism ✓
(mechanism demonstrated on real model traffic), published-baseline
comparison still open (reference number not yet pinned, D10).

## 8. Control arm across the 13 draft repos (run 18, 2026-09-10)

Same verifier and gate as run 17; the 20 earliest tasks of each repo (260
tasks). 260 / 260 scored, 0 errors, 0 truncated file lists (largest tree:
pylint, 2,284 files). Offline rerun byte-identical. Wall time 20.5 min.

| Overall | Value |
|---|---|
| Localization rate (hit@3, file level) | **0.673** |
| False-positive rate (flag level, k = 3; floor ≈ 0.67, D18) | 0.727 |

| Repo | n | hit@3 | FP | note |
|---|---:|---:|---:|---|
| streamlink/streamlink | 20 | 1.00 | 0.63 | ceiling |
| pvlib/pvlib-python | 20 | 0.95 | 0.62 | ceiling |
| deepset-ai/haystack | 20 | 0.80 | 0.71 |  |
| instructlab/instructlab | 20 | 0.80 | 0.58 |  |
| matplotlib/matplotlib | 20 | 0.75 | 0.72 |  |
| pdm-project/pdm | 20 | 0.75 | 0.70 |  |
| sissbruecker/linkding | 20 | 0.70 | 0.68 |  |
| reflex-dev/reflex | 20 | 0.65 | 0.75 |  |
| sphinx-doc/sphinx | 20 | 0.60 | 0.76 |  |
| conan-io/conan | 20 | 0.55 | 0.79 |  |
| keras-team/keras | 20 | 0.55 | 0.76 |  |
| pylint-dev/pylint | 20 | 0.45 | 0.82 |  |
| aws-cloudformation/cfn-lint | 20 | 0.20 | 0.93 |  |

**Provider deviation.** 206 requests were served by Crusoe (bf16) and 54 by
CoreWeave (fp16), the pre-registered fallback, because Crusoe's shared pool
rate-limited during the run. Both are unquantised; every flags row records
`served_by`, so the split is auditable per task. The pre-registered
verifier is therefore "Llama 3.3 70B Instruct, bf16/fp16, served by Crusoe
or CoreWeave in that order, no other providers" (D19).

**Power, from the measured rate.** With p0 = 0.673 and a 15-point lift,
the two-proportion floor is 111 tasks per arm; the 13-repo eval split
(~588 tasks at build = 20) detects ~6.5 points, the 4-repo alternative
(~188) ~11 points. The Gate 4 kill number of 15 points stands; it is
comfortably above the MDE.

**Ceiling.** streamlink (1.00) and pvlib (0.95) leave no room for a 15-point
lift, and haystack/instructlab (0.80) leave exactly 15. A repo at the
ceiling can only show "no lift", which drags the majority-of-repos
criterion regardless of whether memory helps. Options for the
pre-registration, to be decided before publishing it and stated as such:
(a) keep all 13 and accept that the majority criterion is conservative;
(b) drop repos with control hit@3 ≥ 0.90 on Phase 0 data, stating the rule
and the Phase 0 numbers that triggered it; (c) raise k's difficulty by
moving to hit@1 for all repos. (b) is a rule set before the efficacy data
exist, using only control-arm data, so it is not cherry-picking on the
result; it must still be written down before Phase 3 starts (D19).

Gate 0 after run 18: freshness ✓, determinism ✓ on 310 real model calls,
baseline comparison open (D10) — our number is 0.673 hit@3 with Llama 3.3
70B on 13 SWE-bench-Live repos, file level, no hints.
