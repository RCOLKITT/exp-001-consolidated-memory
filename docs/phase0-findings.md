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
| 2026-01-31 Sonnet 5, gated run 5 | — | _fill from results/phase0/5_ |
| 2026-05-31 Opus 5, gated run 6 | — | _fill from results/phase0/6_ |

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
| B. Sonnet 5 on MultiLang 2026 tasks | yes | weak (≤ 5 repos ≥ 20, 1 ≥ 30) | per-language file trees in the adapter | Gated run 5 gives exact chains. Probably 2–3 usable repos at a smaller split; power will be thin. |
| C. Opus 5 on MultiLang after May 2026 | yes | very weak | as B | ~309 tasks in Jun–Jul 2026; gated run 6 gives chains. Likely fails Gate 2 outright. |
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
