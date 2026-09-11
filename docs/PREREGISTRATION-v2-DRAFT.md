# EXP-001 Pre-registration — v2 DRAFT (function-level memory)

**Status (2026-09-11): pre-runs §5.1–5.2 done; the feasibility criterion
(§4) FAILS at the registered pool size — see §11. Not registered, and under
its own rules must not be registered as drafted.** Nothing below binds anyone
until the owner approves a filled-in block and it is tagged `prereg-v2`. Fields
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
| Localization metric | **task-level function-level hit@3**: a task is localized if any flagged `path::qualname` overlaps a non-test **Python-source** gold hunk (same symbol, overlapping span); paired with function-level FP rate at k = 3. A task with no Python gold hunk (docs-only, schema-only patches) is **outside the metric**, not a miss — the verifier's file list is `.py` only, so such a task is unhittable in every arm | this draft; run 23 finding |
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

Note on gold files, found in run 23: v1's file-level gold included non-Python
files (sphinx `CHANGES.rst` was the most frequent "gold file" in its build
window, 14 of 20 tasks; pvlib's `whatsnew/*.rst` likewise). Those files were
never in the verifier's list, so they were unhittable and inflated v1's
recurrence and ceiling (findings §10–11 report them as-is; the registered
v1 result is unaffected because both arms faced the same targets). v2 drops
them at function level, as the metric row says; the file-level secondary in
v2 uses the same Python-only rule and is therefore not exactly v1's metric.

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

## 11. Pre-run outcomes (runs 23–25, 2026-09-11) and the feasibility verdict

Harness exercised on the live path: function-level recurrence over all 13
repos with checkouts (run 23/25, no model), function-level control arm on
run 18's 260 tasks (run 23, 520 calls, 52 min, offline rerun byte-identical),
rescored under the Python-source-only gold rule (run 24, no spend).
Gate 2.3-v2 witness: 50/50 after the witness was fixed for multi-line
signatures (its first pass, 44/50, was wrong on every disagreement; the
`ast` oracle was right on all six — `results/phase0/{23,24}/control/handcheck-functions-verified.csv`).

Filled values (`docs/v2-fill.json`, produced by `phase2.fill_v2` under §4's rules):

| repo | build | eval | p0 (function) | seen2 | ceiling (pts) | Gate 3 floor |
|---|---:|---:|---:|---:|---:|---:|
| aws-cloudformation/cfn-lint | 50 | 59 | 0.250 | 0.322 | 24.2 | 0.108 |
| conan-io/conan | 50 | 115 | 0.400 | 0.139 | 8.3 | 0.065 |
| deepset-ai/haystack | 50 | 38 | 0.650 | 0.316 | 11.1 | 0.095 |
| instructlab/instructlab | 30 | 22 | 0.750 | 0.591 | 14.8 | 0.173 |
| keras-team/keras | 30 | 18 | 0.500 | 0.111 | 5.5 | 0.004 |
| matplotlib/matplotlib | 50 | 51 | 0.500 | 0.196 | 9.8 | 0.028 |
| pdm-project/pdm | 20 | 15 | 0.450 | 0.467 | 25.7 | 0.073 |
| pylint-dev/pylint | 40 | 22 | 0.250 | 0.136 | 10.2 | 0.084 |
| reflex-dev/reflex | 30 | 14 | 0.450 | 0.429 | 23.6 | 0.067 |
| sphinx-doc/sphinx | 20 | 19 | 0.400 | 0.158 | 9.5 | 0.030 |

| ⟦FILL⟧ | value | rule |
|---|---:|---|
| control-arm rate p0 (function level) | **0.436** (eval-weighted; 0.520 over the 252 scored tasks of the 13-repo control run; file-level from the same stage-1 flags 0.710) | §5.2 |
| ceiling on lift | **13.0 pts** | seen2 × (1 − p0), eval-weighted |
| MDE at n = 373 | **10.2 pts** | `phase2.power` |
| kill number | 11 pts | ceil(max(MDE, 0.5 × ceiling)) |
| **feasible** | **NO** — 13.0 < 1.5 × 10.2 = 15.3 | §4 |
| τ | not calibrated — §5.3 is not run when feasibility fails | §5.3 |

**Verdict.** As drafted, v2 cannot be registered: the most a perfect
function-level memory could add on this corpus at this pool is 13 points,
and the pool cannot reliably detect less than 10. The prediction in §5.1
("this check may well fail") held. Functions recur less than files
(eval-weighted seen2 0.26 vs v1's 0.55 at file level, and v1's number was
inflated by non-Python "gold" files), and the lower function-level p0 does
not compensate.

What would make it feasible, computed from the same rules, for the owner
to decide on (none of it is done):
- **More paired tasks.** At p0 0.436 and ceiling 13.0, feasibility needs
  MDE ≤ 8.7 pts, i.e. **n ≥ 521** eval tasks (373 registered). The
  freshness-gated corpus has 1,888 tasks; the 13-repo set was chosen for
  chain length ≥ 30. Adding repos with shorter chains adds eval tasks
  but each with a 20-task build window and its own (small) ceiling; the
  ceiling would need to be re-derived from a new §5.1 run, not assumed.
- **A larger corpus.** SWE-bench-Live adds tasks monthly; a re-pull
  before the hard stop grows both build windows and eval pools, and the
  freshness gate still holds (the verifier's cutoff is fixed). Same rule:
  a new §5.1 and §5.2 before any value is filled.
- **Not an option under these rules:** lowering the 1.5× margin,
  redefining the ceiling, or subsetting to the high-ceiling repos
  (cfn-lint, pdm, reflex) after seeing them.

Nothing was spent on treatment arms. Model calls: 520 (§5.2). The
harness (§3) stays in the repository and is exercised; whichever option
the owner takes reuses it unchanged.

## 12. Sizing option 1 — and two levers outside the one-split design (run 26, 2026-09-11)

All numbers here come from no-model runs (`results/phase0/26/prequential.*`,
run 24's control rates) and the rules in §4. Nothing is registered; the
owner picks a design, then a fresh §5.2/§5.3 fills the block and it is tagged.

**Traditional option 1 is a dead end.** Under the registered split rule
(build 20 for short chains, minimum 10 eval tasks) every repo in the corpus
with a chain of 21–29 tasks contributes fewer than 10 eval tasks and is
excluded. Adding repos leaves the pool at 373 exactly. The corpus has 222
repos and 1,884 tasks after the freshness gate; only 13 chains reach 30.

**Lever 1 — prequential (rolling) evaluation.** Instead of one chronological
split, every task after a 20-task warm-up is an eval task, scored against
the memory built from *all* tasks before it in its repo (memory version
pinned as of task t−1; the task's own gold enters memory only after it is
scored; learning stream = the control arm's flags, so memory content never
depends on its own effect). This is what a deployed memory actually
experiences. Both arms still run on every eval task; pairing, the frozen-
version-per-task rule, seeding and the negative control are unchanged.
Recurrence rises because the window behind each task is the whole chain,
and the pool rises because build tasks are no longer thrown away.

| design | repos | pool (scorable) | p0 (function) | ceiling (pts) | MDE unpaired | ceiling / MDE | feasible (≥ 1.5)? |
|---|---:|---:|---:|---:|---:|---:|---|
| registered split (§11, for reference) | 10 | 373 | 0.436 | 13.0 | 10.2 | 1.27 | **no** |
| **A. prequential, registered 10 repos** | 10 | **530** | 0.442 | **15.6** | **8.6** | **1.82** | **yes** |
| B. prequential, every chain ≥ 21 (p0 of the 11 new repos unmeasured; placeholder 0.439) | 21 | 573 | 0.442 | 15.2 | 8.3 | 1.84 | yes, but needs a control run on 11 more repos first |
| C. prequential, 10 + streamlink + pvlib (ceiling rule re-applied at function level: neither is ≥ 0.90 there) | 12 | 561 | 0.461 | 14.8 | 8.4 | 1.77 | yes |

Per-repo prequential function-level seen2 (pool): conan 0.24 (145),
cfn-lint 0.36 (79), matplotlib 0.15 (79), haystack 0.43 (68), pylint 0.14
(42), instructlab 0.72 (31), keras 0.07 (28), reflex 0.42 (24), sphinx 0.26
(19), pdm 0.60 (15); linkding (negative control) 0.71 (14).

Under §4's rules design A gives kill number **9 pts** (ceil(max(8.6,
0.5 × 15.6))). It changes no threshold, adds no repo, and needs no new
control run: p0 per repo is run 24's. It does need the harness to gain a
rolling evaluation mode (a day's work, offline-testable like §3): learn
online from control flags, pin version t−1 for the treatment arm, N arms,
same `arms.json`.

**Lever 2 — paired power (not used above).** The MDE in every table so far
is the two-proportion formula for *independent* samples. The design is
paired, and paired power depends on the discordance share d (tasks whose
outcome differs between arms), not on p0. At d = 0.5 the two formulas
coincide; v1 observed d = 0.09. For design A: d = 0.2 → MDE 5.4; d = 0.3 →
6.7; d = 0.5 → 8.6 (`phase2.power.mde_paired`). This lever is real but
carries an assumption that only a treatment run can check, so the honest
way to use it is: register an assumed d (say 0.3, well above v1's 0.09 to
allow for function-level volatility), keep the kill number from the
unpaired rule, and report the paired CI as the primary interval — which
`phase4.paired` already does. It is not needed for feasibility of design A
and is offered only because it is the correct power model for this design.

**Lever 3 — class granularity (measured, not proposed).** A `path::Class`
memory (a method's class; a function itself; `<module>`) recurs more than a
function and less than a file: prequential seen2 0.39 vs 0.29 (function)
vs 0.49 (file) over the 24-repo pool. On design A the class-level ceiling
is between 15.1 and 22.1 pts depending on the unmeasured class-level p0
(bounded by the function- and file-level rates). It would need a
class-level control run and a class-level verifier prompt; it is a
different hypothesis, so it is a different registration.

**Recommendation (owner's call): design A**, function level, prequential,
same 10 repos, same negative control, unpaired kill rule, paired CI
reported alongside. Rationale: it is feasible under the rules already
written without touching a single threshold, it uses no unmeasured p0,
and it evaluates the mechanism the way it would be deployed. B adds 43
tasks for the cost of 11 more control runs and a weaker ceiling; C adds
two repos the file-level ceiling rule excluded, which invites the
question of why the rule changed.
