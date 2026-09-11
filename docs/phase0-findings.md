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
the two-proportion floor is 131 tasks per arm (`python -m phase2.power
--p0 0.673 --mde 0.15`); the 13-repo eval split (~588 tasks at build = 20)
detects ~7.4 points, the 4-repo alternative (~188) ~12.7 points. The Gate 4
kill number of 15 points stands; it is above the MDE in both designs.

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

## 9. Cross-run determinism and the hand-check sample (run 19)

Run 19 re-scored run 18 entirely from run 18's cached responses on a
different runner, offline (260 cache hits, 0 misses): flags sha256
`86ede91e…`, identical to run 18. It also wrote
`results/phase0/19/control/handcheck.csv`: 50 flags sampled with seed 1,
each with the oracle's label and the gold files. Gate 2.3 needs a human to
fill the `manual` column by reading each gold patch, then
`python -m phase2.handcheck score handcheck.csv` (≥ 0.95 required).

## 10. Gold-location recurrence — the ceiling on file-level memory (run 20)

`python -m phase2.recurrence` on the gated corpus, 13 draft repos. For each
build prefix N: how many gold files recur ≥ 3 times among the first N tasks
(the only patterns the §6 promotion rule can consolidate), and the share of
the remaining tasks whose gold file is one of them (`seen3`). A promoted
file memory can only help a task whose gold file it names, and only if the
control arm missed it, so **ceiling ≈ seen3 × (1 − p0)** with p0 the
repo's control hit@3 from run 18.

| repo | chain | build N | eval n | files ≥ 3 in build | seen3 | p0 | ceiling (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|
| conan-io/conan | 165 | 20 | 145 | 0 | 0.00 | 0.55 | 0.0 |
| conan-io/conan | 165 | 40 | 125 | 3 | 0.05 | 0.55 | 2.2 |
| conan-io/conan | 165 | 60 | 105 | 10 | 0.11 | 0.55 | 5.1 |
| aws-cloudformation/cfn-lint | 109 | 20 | 89 | 2 | 0.17 | 0.20 | 13.5 |
| aws-cloudformation/cfn-lint | 109 | 40 | 69 | 4 | 0.22 | 0.20 | 17.4 |
| aws-cloudformation/cfn-lint | 109 | 60 | 49 | 14 | 0.39 | 0.20 | 31.0 |
| matplotlib/matplotlib | 101 | 20 | 81 | 2 | 0.18 | 0.75 | 4.6 |
| matplotlib/matplotlib | 101 | 40 | 61 | 4 | 0.31 | 0.75 | 7.8 |
| matplotlib/matplotlib | 101 | 60 | 41 | 13 | 0.54 | 0.75 | 13.4 |
| deepset-ai/haystack | 88 | 20 | 68 | 1 | 0.06 | 0.80 | 1.2 |
| deepset-ai/haystack | 88 | 40 | 48 | 7 | 0.25 | 0.80 | 5.0 |
| deepset-ai/haystack | 88 | 60 | 28 | 11 | 0.36 | 0.80 | 7.1 |
| pylint-dev/pylint | 62 | 20 | 42 | 2 | 0.29 | 0.45 | 15.7 |
| pylint-dev/pylint | 62 | 40 | 22 | 9 | 0.32 | 0.45 | 17.5 |
| instructlab/instructlab | 52 | 20 | 32 | 6 | 0.62 | 0.80 | 12.5 |
| instructlab/instructlab | 52 | 40 | 12 | 14 | 0.50 | 0.80 | 10.0 |
| keras-team/keras | 48 | 20 | 28 | 0 | 0.00 | 0.55 | 0.0 |
| reflex-dev/reflex | 44 | 20 | 24 | 5 | 0.54 | 0.65 | 19.0 |
| streamlink/streamlink | 41 | 20 | 21 | 0 | 0.00 | 1.00 | 0.0 |
| sphinx-doc/sphinx | 39 | 20 | 19 | 3 | 0.95 | 0.60 | 37.9 |
| pdm-project/pdm | 35 | 20 | 15 | 5 | 0.53 | 0.75 | 13.3 |
| sissbruecker/linkding | 34 | 20 | 14 | 9 | 0.43 | 0.70 | 12.9 |
| pvlib/pvlib-python | 30 | 20 | 10 | 8 | 0.40 | 0.95 | 2.0 |

Aggregate over repos with ≥ 10 eval tasks at that prefix:

| design | eval pool | ceiling |
|---|---|---|
| build = 20 | 588 eval tasks | ceiling on aggregate lift ≈ 7.3 pts |
| build = 40 | 337 eval tasks | ceiling on aggregate lift ≈ 8.0 pts |
| build = 60 | 223 eval tasks | ceiling on aggregate lift ≈ 12.6 pts |

Reading: at build = 20 the pre-registered 15-point kill number is above
the ceiling in most repos and in aggregate — Gate 4 would fail by
construction, not by evidence. Directory-level recurrence is far higher
(`recurrence.md`, `dir seen3` 0.4–1.0) but a directory hint is weak
localization information when the verifier already sees the whole tree.

What this changes before pre-registration:
1. Build split per repo should be as long as the chain allows while
   leaving ≥ 20 eval tasks: 60 for conan, cfn-lint, matplotlib, haystack,
   pylint; 40 for instructlab, keras, reflex, streamlink; 20 for sphinx,
   pdm, linkding, pvlib. The eval pool shrinks (fewer tasks per arm) and
   the MDE rises accordingly — recompute with `phase2.power`.
2. The Gate 4 kill number must be compared with the ceiling *before* it is
   fixed; "15 points" was written without this bound. Lowering a kill
   number before pre-registration on Phase 0 evidence is legitimate;
   lowering it after Phase 4 is not (§7).
3. The unit of memory is the file (D24); a symptom-level memory would have
   a strictly lower ceiling.

## 11. Ceiling versus detectable effect (the pre-registration problem)

Minimum detectable effect from `phase2.power` at p0 = 0.673 (two-sided
α 0.05, power 0.8), against the ceiling from §10:

| design | eval pool | MDE (pts) | ceiling at promotion ≥ 3 (pts) |
|---|---:|---:|---:|
| build 20, 13 repos | 588 | 7.4 | 7.3 |
| build 40 | 337 | 9.7 | 8.0 |
| build 60 | 223 | 11.7 | 12.6 |

In every design the smallest lift the evaluation could detect is about
equal to the largest lift file-level promoted memory could produce. The
spec's 15-point kill number is above both. As written, Phase 4 cannot
return a positive result on this corpus; a null would be uninformative
because it is also what an underpowered design returns.

This is a Phase 0/2 finding, before pre-registration and before Phase 3–4
spend, which is where the spec wants it found. Levers, all of which must
be fixed in the pre-registration and none of which touch the gate or the
freshness rule:

- **Promotion at ≥ 2 occurrences** (§6.1 is adapter config): raises the
  ceiling — run 21 quantifies it (`results/phase0/21/recurrence.md`).
- **Longer chains**: more corpus (option D, build fresh tasks for the
  long-chain repos) raises both the ceiling and the power.
- **A per-task outcome that memory can move more often**: e.g. hit@1 or
  reciprocal rank, where re-ranking a file already in the top 3 counts.
  Changes the primary metric; must be pre-registered with its own ceiling.
- **Accept the bound and pre-register the mechanism paper as the primary
  deliverable** (spec Phase 5: Gate 1 alone justifies it), running Phase
  3–4 as a bounded, honest efficacy check with the ceiling stated.

Owner decision. What is not a lever: lowering the kill number after data,
or relaxing the freshness gate.

### 11.1 Ceilings at promotion ≥ 2 (run 21)

| build N | eval pool | MDE (pts) | ceiling, promote ≥ 3 | ceiling, promote ≥ 2 |
|---:|---:|---:|---:|---:|
| 20 | 588 | 7.4 | 7.3 | 10.5 |
| 30 | 440 | 8.6 | 8.0 | 12.5 |
| 40 | 337 | 9.7 | 8.0 | 14.2 |
| 50 | 275 | 10.7 | 9.5 | 17.3 |
| 60 | 223 | 11.7 | 12.6 | 17.4 |

With promotion at two occurrences from two distinct tasks, build 40–50
gives a ceiling 4–7 points above the MDE — a design that can detect its
own maximum effect. Per repo the room is very uneven (build 40, ≥ 2):
cfn-lint 31 pts (control 0.20), pylint 20, matplotlib 12, instructlab 10,
conan 8, haystack 7. The majority-of-repos criterion will be decided by
the repos with little room, which argues for reporting per-repo lift
against per-repo ceiling rather than a bare majority.

Recommended pre-registration design (owner to confirm):
- promotion: ≥ 2 `bad` records from ≥ 2 distinct tasks (§6.1–6.2 set to 2);
  every other §6 rule unchanged;
- build split: 50 for repos with ≥ 70 tasks (conan, cfn-lint, matplotlib,
  haystack), 40 for pylint, 30 for instructlab / keras / reflex /
  streamlink / sphinx, 20 for pdm / linkding / pvlib — eval pool ≈ 300;
- kill number: ≥ 10 points aggregate lift (MDE ≈ 10.5 at that pool) with
  the ceiling (~15 at that mix) stated next to it; FP ceiling unchanged;
- per-repo reporting of lift / ceiling; negative control unchanged.

## 12. End-to-end smoke with file-keyed consolidation (experiment run 4)

pvlib, pdm, haystack; build 20, eval 8 per repo; pinned verifier and seam;
promotion at ≥ 3 (the pre-D24 setting). Cost: ~110 model calls.

| repo | candidates | discard rate | promoted | memories |
|---|---:|---:|---:|---|
| pvlib | 56 | 0.57 | 3 | spectrum/__init__, spectrum/mismatch, solarposition |
| pdm | 60 | 0.47 | 1 | cli/commands/run |
| haystack | 60 | 0.38 | 1 | core/pipeline/pipeline |

Every promoted memory carries only `bad` records (§6.5 held), three
supports from three distinct tasks, and reads as a defect pattern
(`symptom => file :: reason`). In evaluation the treatment arm retrieved
memory on 24 / 24 tasks and its flags differed from control on 17 / 24.
Aggregate on 24 tasks: lift +4.2 pts, FP −3.2 pts (pdm +12.5, others 0) —
a smoke, not a result. The mechanism the experiment needs is now
demonstrated on real traffic: consolidate → freeze → pin → retrieve →
paired arms.

Gate 3 note: with file-keyed consolidation the discard rate is the share
of candidates that repeat an already-seen file. On 20-task builds it is
0.38–0.57, below the spec's "> 60%" expectation, which was written for a
semantic seam; longer builds raise it (a repeat is only possible once a
file has been seen). The pre-registration should restate Gate 3's floor
for the file-keyed seam or tie it to build length.

## 13. Published baseline, recomputed from the authors' artifacts (baseline run 1)

arXiv and its mirrors are unreachable from the authoring session, so the
reference was **recomputed** rather than copied: the Agentless v1.5.0
release (`agentless_swebench_lite.zip`, published 2024-10-29) contains the
file-level localization outputs (`found_files`) for all 300 SWE-bench Lite
instances, produced with GPT-4o. Scoring them with `phase2.baseline_agentless`
— the same hit@k / flag-level FP definitions as our control arm — against
SWE-bench Lite's gold patches (`princeton-nlp/SWE-bench_Lite`, test split):

| Agentless output | n | hit@1 | hit@3 | hit@5 | FP@3 |
|---|---:|---:|---:|---:|---:|
| LLM file-level only (`file_level/loc_outputs.jsonl`, v1.5) | 300 | 0.640 | **0.787** | 0.827 | 0.728 |
| LLM + embedding retrieval, combined (`combined_locs.jsonl`, v1.5) | 300 | 0.630 | 0.817 | 0.850 | 0.728 |
| v0.1.0 (July 2024) file-level | 300 | 0.653 | 0.777 | 0.827 | 0.729 |

Our control arm (run 18): Llama 3.3 70B, file list only, 13 SWE-bench-Live
repos gated after 2023-12-31, 260 tasks: **hit@3 0.673, FP@3 0.727**.

Gate 0.1 reading: the LLM-only Agentless number is the closest published
analogue (same task shape: issue + repository file tree → ranked files, no
hints). Our rate is 11 points lower with a weaker, freshness-compliant
model on newer tasks, and the false-positive profile is the same to three
decimals — the harness is measuring the same quantity. Recorded as
**within a defensible margin**, with the two confounds (model, corpus)
stated. `results/baseline/1/baseline-10.json` is the reference file.

## 14. Gate 3 on the registered run (experiment run 5, 2026-09-10)

Registered config (`docs/exp-run.prereg.json`, sha256 a7846653…), byte-identical
to the tagged block. Ceiling rule dropped streamlink (1.00) and pvlib (0.95)
as registered; linkding is the negative control and built no memory.
Learning ran on 10 treatment repos, 370 build tasks, one kernel per repo.

| repo | build | candidates | discard rate | promoted | floor (≥0.40, ≥2) |
|---|---:|---:|---:|---:|---|
| aws-cloudformation/cfn-lint | 50 | 143 | 0.41 | 3 | pass |
| conan-io/conan | 50 | 129 | 0.35 | 1 | **fail** (both) |
| deepset-ai/haystack | 50 | 150 | 0.46 | 11 | pass |
| instructlab/instructlab | 30 | 89 | 0.60 | 7 | pass |
| keras-team/keras | 30 | 86 | 0.23 | 1 | **fail** (both) |
| matplotlib/matplotlib | 50 | 135 | 0.64 | 7 | pass |
| pdm-project/pdm | 20 | 60 | 0.45 | 4 | pass |
| pylint-dev/pylint | 40 | 113 | 0.73 | 4 | pass |
| reflex-dev/reflex | 30 | 88 | 0.57 | 4 | pass |
| sphinx-doc/sphinx | 20 | 56 | 0.32 | 3 | **fail** (discard) |

Gate 3 passes on 7 of 10 treatment repos and fails on conan, keras and
sphinx. Every promoted memory (45 in total) carries only `bad` records
from ≥ 2 distinct tasks, was proposed by `verifier:<model>` and approved
by `promotion-gate` (separation of duties held), and reads as a defect
pattern, e.g. pylint: "Crash on `enumerate(x, int(y))` =>
pylint/checkers/refactoring/refactoring_checker :: the stacktrace points to
this file". Kernels, diagnose and gate3 files:
`results/experiment/5/learn/<repo>.{kernel,diagnose,gate3}.json`.

What the failures mean. Discard rate under file-keyed consolidation is
the share of candidates that name an already-seen file; a low rate means
the verifier's wrong guesses on that repo are spread over many files, so
few files recur and few memories can form. conan (large, flat `conans/`
tree) and keras (per-backend `numpy.py` duplicates) both show this; sphinx
sits on the shortest build (20 tasks) where a repeat is rarely possible.
These are properties of the repo and the build length, not of the gate
thresholds — Θ/ρ are inert under the file-keyed seam (D24).

Consequence for Gate 4 (fixed before any further Gate 4 numbers were read;
see D28): the primary analysis stays as registered — aggregate lift over
all 10 treatment repos, kill number 10 pts. A secondary, clearly labeled
breakdown reports the same metrics over the 7 repos that passed Gate 3.
Nothing is excluded from the primary analysis after the fact.

Evaluation on run 5 completed only conan (n = 115: control 0.561, treatment
0.596, lift +3.5 pts, FP −0.6 pts) before the verifier returned truncated
JSON on cfn-lint and the run aborted. The fix (salvage the ordered path
list from truncated output; a task whose call fails is dropped from both
arms, never one) is in main, and run 6 resumes evaluation from the run 5
kernels and caches (`learn_run = 5`, `resume.json`), so the registered
learning phase is not repeated or re-randomized.

## 15. Gate 4 — the registered result (experiment runs 6 + 7, 2026-09-11)

Run 6 evaluated both arms on every eval task of the registered split from
run 5's frozen kernels (`resume_of: 5`); run 7 is the paired task-level
analysis of run 6 with no model calls (`results/experiment/7/paired/`).
Registered pool 373 tasks; 372 were evaluated (one conan task has no
non-test gold file and is outside the metric by definition, D9) and 371
scored (one cfn-lint task, `aws-cloudformation__cfn-lint-3712`, failed in
both arms after the verifier returned truncated JSON that the salvage
could not recover; dropped from both arms, recorded in `arms.json:
errors`).

| criterion (registered) | value | verdict |
|---|---:|---|
| localization lift, aggregate over 10 treatment repos | **+1.08 pts** (control 0.644 → treatment 0.655, n = 371) | **fails** kill number ≥ 10 |
| 95% CI on the lift (paired Wald / bootstrap over tasks) | −2.0 to +4.2 / −1.9 to +4.3 | excludes 10 |
| discordant pairs | treatment-only hit 19, control-only hit 15; McNemar exact p = 0.61 | no effect detectable |
| false-positive rise (flag level, k = 3) | +0.1 pts (0.741 → 0.742) | passes ceiling ≤ 5 |
| effect in a majority of repos | lift > 0 in 3 of 10 (conan, keras, pylint); < 0 in 3; = 0 in 4 | **fails** |
| negative control (linkding, n = 14) | lift 0.00, FP rise 0.00; flags identical on 14/14, no memory retrieved | passes |
| secondary: 7 repos that passed Gate 3 (n = 220) | lift −0.45 pts (CI −3.7 to +2.8); trt-only 6, ctl-only 7 | no effect |

Per repo (n, control, treatment, lift; from `paired.md`): cfn-lint 58,
0.362, 0.328, −3.5; conan 114, 0.561, 0.597, +3.5; haystack 38, 0.974,
0.974, 0; instructlab 22, 0.682, 0.682, 0; keras 18, 0.667, 0.722, +5.6;
matplotlib 51, 0.843, 0.843, 0; pdm 15, 0.600, 0.533, −6.7; pylint 22,
0.636, 0.773, +13.6 (3 treatment-only hits, 0 control-only, p = 0.25);
reflex 14, 0.714, 0.643, −7.1; sphinx 19, 0.737, 0.737, 0.

**Verdict: the registered hypothesis is killed.** Under the pre-registered
design, consolidated file-level memory of prior defects does not raise
localization by the kill number; the point estimate is one tenth of it and
the interval excludes it. The secondary criteria are informative: the
false-positive rate did not move and the negative control is exactly
inert, so the mechanism is clean — it simply does not help at this
granularity. The one repo with a visible lift (pylint, +13.6) is 3
discordant tasks and is not distinguishable from noise.

What the paired data say about why. The treatment arm retrieved memory on
371/371 tasks and changed its flags on 283/371 (76%), so memory was
present and acted on; it moved answers roughly symmetrically in both
directions (19 vs 15). The ceiling analysis (§10–11) put the maximum
possible lift at ≈ 17.9 pts if every recurring gold file were flagged;
the realized share of that ceiling is ≈ 6%. Two mechanisms are visible in
the per-task rows: (a) a promoted memory names a file that recurs in the
build window but not in this task, and the verifier substitutes it for a
correct guess (the 15 control-only losses); (b) the memories are
`symptom => file` at file granularity, and on repos where the control
already localizes well (haystack 0.97, matplotlib 0.84) there is nothing
left to gain. Both are properties of the file-level design, not of the
kernel's gates, which behaved as specified throughout (§14).

Not done and not claimed: no post-hoc re-tuning of Θ/ρ/promotion, no
subset selection, no second registered run. The hard stop is 2026-10-22;
any follow-up (function-level memory, retrieval-gated injection, larger
build windows) is a new pre-registration, not an amendment.

Open item: the salvage regex did not recover `cfn-lint-3712`; the raw
response is in the `eval-6` artifact cache (`runs/eval/.../cache.jsonl`)
and should be inspected before the next run so the parser covers that
shape too.


## 16. v2 pre-runs at function granularity (runs 23–25, 2026-09-11)

Run 23 exercised the v2 harness live: function-level recurrence over the
13 repos with checkouts (3 min, no model), then a two-stage control arm on
run 18's 260 tasks (520 calls, 52 min; offline rerun byte-identical). Run
24 rescored it under the corrected gold rule (Python-source hunks only;
docs-only tasks leave the metric — 4 tasks); run 25 recomputed recurrence
with the same rule and the build repeat share. Four tasks errored in the
function stage on truncated JSON the salvage could not read (the raw text
is now kept in the error message for the next run).

Function-level control: 0.520 hit@3 over 252 tasks (FP 0.713); the same
stage-1 flags give 0.710 at file level (v1 run 18: 0.673 on 260). The
stage-1 prompt is byte-identical to v1's; the difference is provider
non-determinism at temperature 0 (235/256 same top-1 file, 132/256
identical lists, 0.84 flag overlap with run 18), not the prompt.

Recurrence at function level, eval-weighted seen2 at the registered build
sizes: 0.26 (file level, v1: 0.55 — and that included non-Python files
such as sphinx's `CHANGES.rst`, gold in 14/20 build tasks and unhittable).
Ceiling 13.0 pts against an MDE of 10.2 at n = 373: the draft's
feasibility rule (ceiling ≥ 1.5 × MDE) fails; n ≥ 521 would be needed at
this ceiling. Recorded as the outcome of v2-as-drafted in
`docs/PREREGISTRATION-v2-DRAFT.md` §11 and D32; no treatment arm was run
and no τ was calibrated.

Gate 2.3-v2 tooling: the indentation-based witness first disagreed with
the `ast` oracle on 6/50 hunks; all six were witness bugs (multi-line
signatures, nested defs), fixed; second pass 50/50. The `ast` mapping was
right on every sampled hunk.
