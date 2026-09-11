# EXP-001 Pre-registration — v2 DRAFT (function-level memory)

**Status:** DRAFT — not registered. Nothing below binds anyone until the
owner approves the filled-in block and it is tagged `prereg-v2`. Fields
marked ⟦FILL⟧ are set by the three no-treatment pre-runs in §5 and then
frozen; the *rules* for filling them are fixed here so that no value is
chosen after any treatment result is seen. v1 (`docs/PREREGISTRATION.md`,
tag `prereg-v1`) stands as registered and is not amended by this document.

## 1. Why a v2

v1 killed its hypothesis cleanly (findings §15, D30): file-level memory of
prior defects moved the verifier's flags on 76% of tasks but the moves
were symmetric (19 treatment-only hits vs 15 control-only), lift +1.08 pts
against a kill number of 10, FP flat, negative control inert. The kernel's
gates behaved as specified; the granularity did not carry enough
information. Two facts from the v1 data motivate the two changes below,
and only these two:

1. **Granularity.** A file-level memory says "issues like this land in
   `lib/matplotlib/axes/_axes.py`". On repos where the control arm already
   names that file (haystack 0.97, matplotlib 0.84) this adds nothing; on
   the rest it competes with a correct file for one of three slots. A
   function-level memory ("…land in `_axes.py::Axes.boxplot`") is a claim
   the control arm cannot make from a file listing alone, so it has room
   to help exactly where v1 had none.
2. **Unconditional injection.** v1 injected the top-3 memories on 371/371
   tasks regardless of how similar they were to the issue. The 15
   control-only losses are consistent with a low-similarity memory
   displacing a correct guess. v2 injects only above a similarity
   threshold τ, set from build tasks before registration (§5.3).

Everything else is inherited from v1 unchanged so that the two runs are
comparable: corpus, freshness gate, verifier model and serving, embedding
model, promotion policy, TTL, split rule, negative control, seed, kill
logic. v2 is a **new registration**, not an amendment: v1's evaluation
outcomes were not used to choose any v2 value, and this document says
where every value comes from.

## 2. Hypothesis

**H2.** With the same verifier, corpus and split as v1, a per-repository
kernel that consolidates *function-level* defect memories
(`symptom => path::qualname :: reason`) and injects them only when
retrieval similarity ≥ τ raises task-level **function-level hit@3** by at
least the kill number (§4) over a paired control, without raising the
function-level false-positive rate by more than 5 pts, on a negative
control that shows no lift.

**Falsification.** If aggregate function-level lift < kill number, H2 is
dead. There is no "trend" reading. If the feasibility check in §5.1 fails,
the run is not made and that is recorded as the result of v2.

**Attribution (secondary, descriptive).** A third arm, function-level
memory injected *unconditionally* (τ = 0), is evaluated on the same tasks
so that any effect can be attributed to granularity vs gating. It is not a
registered criterion and cannot rescue H2.

## 3. What changes in the harness (before any pre-run)

| Change | Where | Test |
|---|---|---|
| Function-level ground truth: each non-test gold hunk maps to the enclosing top-level `def`/`class`…`def` at `base_commit` via `ast`; a hunk outside any function maps to `path::<module>`; gold = set of such locations with the function's line range | `phase0/ground_truth.py` (`gold_functions`) | golden vectors on 20 hand-labelled hunks (§6, Gate 2.3-v2) |
| Verifier v2, two stages, identical in both arms: stage 1 ranks files from the listing (v1 prompt); stage 2 shows the `def`/`class` index of the top-3 files and asks for up to 3 `path::qualname` flags with reasons | `phase0/verifier.py` (`LocalizerV2`) | prompt snapshot test; JSON salvage covers `qualname` |
| Flags carry `Location(path, def_start, def_end, symbol)`; gold hunks are symbolised the same way (lazy, memoised). The oracle gains **one clause**: when both sides name a symbol they must be equal — otherwise a `<module>` flag would earn file-level credit. File-level flags (no symbol) keep v1 semantics exactly, which is what the file-level secondary metric relies on | `adapters/code/oracle.py`, `phase0/ground_truth.py` | `tests/test_functions.py::test_oracle_symbol_clause` |
| Function index cache (`functions.jsonl`, keyed by repo/commit/path) saved with every run so replays never need the checkout | `phase0/functions.py` | cache round-trip test |
| Gate 2.3-v2 tooling: `handcheck export-functions` (50 gold hunks → oracle symbol + source context for the human read) and `verify-functions` (indentation-based symboliser, independent of `ast`) | `phase2/handcheck.py` | agreement with `ast` on a fixture; scoring test |
| Consolidation keyed by `(path, qualname)`; retrieval by embedding cosine of issue text vs memory content (as v1) | `adapters/code/similarity.py` (`FunctionKeyedSimilarity`) | seam test: same function ⇒ 1.0 |
| Retrieval gate τ: a memory is injected only if cosine ≥ τ; `retrieved` records the score and whether it passed | `adapters/code/pipeline.py` | test: τ = 1.01 ⇒ never injected, arms identical |
| Three-arm evaluate (control / gated / ungated), interleaved per task, seeded; per-task hits written to `arms.json` so `phase4.paired` needs no corpus | `phase4/evaluate.py`, `phase4/paired.py` | pairing test extended to three arms |
| Function-level recurrence report (`recurrence.py --level function`) and function-level control run (`run_control.py --level function`) | `phase2/recurrence.py`, `phase0/run_control.py` | offline tests on synthetic chains |
| Workflow keys: `granularity: "function"`, `tau`, `arms: ["control","gated","ungated"]` | `.github/workflows/experiment.yml`, `phase0.yml` | yaml lint |

Cost of the harness work is engineering time only; no model spend.

**Status (2026-09-11): built and tested offline end to end** (learn →
evaluate → paired at function granularity through the real CLIs against a
local git repo and a stub model; 94 tests). Workflow keys: `.exp-run.json`
`granularity`, `tau`, `arms`; `.phase0-run.json` `level`, `ceiling_metrics`.
v1 replays are byte-identical: record ids, prompts and cache keys are
unchanged at file granularity, and the v2 stage-1 request is the v1 request,
so v1's control caches serve stage 1 of the function-level control run.
Not yet exercised on the live path (a runner + the real verifier); the
first pre-run (§5.1, no model) is that exercise.

## 4. Values (inherited unless marked)

| Item | Value | Source |
|---|---|---|
| Corpus, freshness gate, verifier model, serving, providers, `served_by` rule | as v1 | v1 block |
| Verifier prompt | **v2 two-stage** (§3); treatment differs from control only by the memory section, injected at both stages | this draft |
| Localization metric | **task-level function-level hit@3**: a task is localized if any flagged `path::qualname` range overlaps a non-test gold hunk; paired with function-level FP rate at k = 3 | this draft |
| Secondary metric | file-level hit@3 recovered from the same flags (so v1 and v2 controls can be compared) | this draft |
| Embedding model / revision | as v1 (MiniLM `1110a243…`) | D20 |
| Consolidation seam | **function-keyed**: same `(path, qualname)` ⇒ same pattern | §3 |
| Retrieval gate τ | ⟦FILL from §5.3⟧ | this draft |
| Θ / ρ / cluster | as v1 (inert under keyed consolidation) | D23 |
| Promotion | ≥ 2 `bad` records from ≥ 2 distinct tasks; bad only; separation of duties | §6, D25 |
| TTL | 30 ticks | D4 |
| Memory scope | one kernel per repository | §1 |
| Ceiling rule | repos with **function-level** control hit@3 ≥ 0.90 in §5.2 excluded (expected: none) | D19 |
| Build split rule | as v1: 50 / 40 / 30 / 20 by chain length; **same build/eval membership as v1** (`results/experiment/5/split.json`) | findings §11.1 |
| Negative control | sissbruecker/linkding | v1 |
| Evaluation | three arms on every eval task, interleaved, seeded (**seed 11**; a new seed so the interleaving order is not v1's) | Phase 4 |
| Control-arm rate (function-level) | ⟦FILL from §5.2⟧ — expected well below v1's 0.644 | §5.2 |
| Treatment eval pool | 373 tasks, 10 repos (as v1; minus tasks with no non-test gold hunk) | v1 |
| Minimum detectable effect | ⟦FILL⟧ = `phase2.power mde_at(p0 = §5.2 rate, n = pool)` | `phase2.power` |
| Ceiling on lift (function-level, promote ≥ 2) | ⟦FILL from §5.1⟧ = seen2_function × (1 − p0) | `phase2.recurrence` |
| **Kill number** | ⟦FILL⟧ = **max(MDE, 0.5 × ceiling), rounded up to the next whole point**; fixed before tagging, never lowered | rule fixed here |
| False-positive ceiling | rise ≤ 5 pts absolute (paired, same k, function level) | Gate 4 |
| Majority criterion | lift > 0 in a majority of treatment repos | Gate 4 |
| Negative-control criterion | lift = 0 within noise on linkding | Gate 4 |
| Gate 3 floor | ≥ 2 promoted memories per treatment repo; discard-rate floor ⟦FILL⟧ = 0.5 × the build-window repeat share from §5.1, per repo | rule fixed here |
| Feasibility criterion (new) | run only if ⟦ceiling⟧ ≥ 1.5 × ⟦MDE⟧; otherwise v2 is recorded as "not feasible at function level with this corpus" and closed | §5.1 |
| Hard stop | six weeks from the `prereg-v2` tag | v1 §10 |

Why `max(MDE, 0.5 × ceiling)`: v1 set 10 against MDE 9.2 and ceiling 17.9
by judgement. Writing the rule down removes the judgement: the kill number
must be detectable (≥ MDE) and must demand that memory realize at least
half of what recurrence makes possible.

## 5. Pre-runs that fill the ⟦FILL⟧ fields (no treatment, no eval-task outcomes)

All three run on GitHub Actions, results committed under `results/`, and
none of them evaluates a treatment arm or looks at v1's eval-arm outcomes.

### 5.1 Function-level recurrence (no model calls)
`phase2.recurrence --level function` over the v1 chains and split:
for each repo, the share of eval tasks whose gold *function* was a gold
function ≥ 2 times in its build prefix (`seen2_function`), and the
build-window repeat share (candidates that name an already-seen function).
Fills: ceiling, Gate 3 discard floor, feasibility. Prediction, stated now
so it can be wrong: functions recur less than files, so `seen2_function`
will be roughly half of v1's file-level 0.55 aggregate, putting the
ceiling near 8–12 pts against an MDE that will be higher than v1's
(lower p0 ⇒ larger variance at fixed n). **The feasibility check may fail.**
If it does, the honest outcome is "function-level memory cannot be tested
on this corpus at this n", and the next design question is corpus size,
not memory design.

### 5.2 Function-level control arm (≈ 260 model calls)
`run_control --level function` on the same 260 tasks as v1's run 18 (first
20 per repo, 13 repos): fills p0, MDE and the ceiling-rule check; also
yields the file-level rate from the same flags, which must be within noise
of v1's 0.673 or the two-stage prompt has changed the file stage and must
be explained before registration.

### 5.3 τ calibration (build tasks only, ≈ 370 model calls, or 0 if reusing v1 caches)
On the **build** tasks of each repo (never eval tasks), replay v1's
learn pass with function-keyed consolidation to obtain promoted memories,
then for each build task compute the cosine between issue text and each
promoted memory, labelled by whether that memory's function overlaps the
task's gold. τ = the cosine at which precision of "memory names a gold
function" first reaches 0.5 on build tasks, pooled across repos, rounded
to 0.05; if precision never reaches 0.5, τ = the 90th percentile of
non-matching cosines. Fixed once; identical in every repo.

## 6. Gates before Phase 3-v2 starts

- **Gate 0.1-v2** baseline reference: Agentless v1.5 function-level
  localization recomputed from the same `loc_outputs.jsonl` used in D26,
  with our function oracle; reported, not a criterion.
- **Gate 2.3-v2** oracle hand-check: 50 gold hunks → function mappings
  read by a human (owner or delegate) against the pre-image source; ≥ 95%
  agreement; independent `ast` re-derivation on the runner as in D27.
- **Gate 3-v2** as §4; expected failure point remains here.
- **Feasibility** as §5.1.

## 7. Analysis plan (fixed)

Primary: aggregate function-level lift, gated arm vs control, over the 10
treatment repos, against the kill number; paired Wald and bootstrap 95%
CIs and exact McNemar reported (`phase4.paired`). Secondary, descriptive:
ungated arm vs control; file-level lift from the same flags; per-repo
table against per-repo ceilings; passed-Gate-3 subset. No subsetting, no
re-tuning, no second registered run under this tag.

## 8. Cost and time

Model calls: 5.2 ≈ 260; 5.3 ≤ 370; learn ≈ 370; three-arm eval ≈ 1,120.
At v1's observed rate (run 6: ≈ 750 calls in 35 min) the registered run is
under two hours of runner time; OpenRouter spend at v1's rate was small
and will be reported from the provider dashboard. Engineering (§3) is the
larger cost: roughly a day of harness work plus the hand-check.

## 9. Draft run configuration

`docs/exp-run.v2.draft.json` mirrors `docs/exp-run.prereg.json` with the
new keys; the ⟦FILL⟧ values are `null` until §5 completes. The registered
run's `config.json` must equal the final file byte for byte.

## 10. Sign-off (unfilled)

- Drafted by: Claude (session), on the owner's instruction, 2026-09-11
- Approved by owner: ______ (date)
- Registered commit / tag `prereg-v2`: ______
