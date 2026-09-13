# EXP-001 Pre-registration — v3 DRAFT (veto memory)

**Status:** DRAFT — not registered. This document fixes every rule before
any held-out data is touched, and it says up front what the development
data predict: the veto's advantage over a memory-free placebo is small and,
for the safer variant, below what the held-out pool can detect (§7). The
owner decides whether that is worth a run (§9). v1 and v2 stand as
registered (`prereg-v1`, `prereg-v2`).

## 1. Thesis, inverted

v1 and v2 asked memory to point *at* the gold and found it could not: the
gold rarely recurs at a granularity the verifier can use (findings §15,
§20), and the verifier reacts to a memory section's presence more than its
content (placebo arm, §20). The same runs show the opposite regularity is
strong: the verifier's *wrong* guesses recur. A file it has blamed wrongly
twice, and never rightly, is wrong again 9 times in 10 when it blames it
next (findings §21). A veto memory remembers those files and suppresses
them. It needs nothing from the verifier — it acts on the output — so the
perturbation channel v2 exposed is closed by construction.

**H3.** A per-repository veto memory, consolidated from the verifier's own
confirmed false positives, lowers the flag-level false-positive rate
relative to (a) the unfiltered control and (b) a placebo that removes the
same number of flags at the same ranks at random, at a smaller cost in
task-level hit@3 than the placebo, on repositories the rule was never
developed on.

## 2. Development set vs held-out set (the honesty structure)

Every rule below was chosen on the **development set**: the 10 v1/v2
treatment repos, using v1's file-level control flags (phase0 run 18 for
tasks 1–20, experiment run 6 for the eval tasks; 378 scored tasks, 1,057
flags) and v2's gold keys. The **held-out set** is every other repository
in the freshness-gated corpus with a chain of ≥ N tasks (§4); none of its
flags or gold have been looked at. The registered run scores the held-out
set only. Development-set numbers are predictions, not results.

## 3. Mechanism (kernel terms)

| Item | Value |
|---|---|
| Evidence | every control-arm flag becomes a record; the oracle labels it `good` (false positive) or `bad` (correct), as in v1/v2 |
| Veto memory | a promoted cluster of **`good`** records for the same file (file-keyed consolidation, D24) from **≥ 2 distinct tasks**, with **no `bad` record for that file** — the contradiction seam (§6 of the spec) blocks promotion while a correct flag for the file exists, and a later correct flag supersedes an existing veto (kernel `supersede`, ledgered) |
| Application (the "filter" arm) | after the control arm answers, any flag whose file has a live veto is removed; **rank-1 is never removed** (variant P) or may be (variant U) — see §5 |
| Timing | prequential: the veto in force at task t is the snapshot after task t−1; the task's own labels enter after scoring; warm-up 0 (every task scored; early tasks have no vetoes and equal control) |
| Learning stream | the control arm's flags only |
| Provenance | every veto lists its supporting record ids; `arms.json` records, per task, which flags were removed and by which veto |
| Cost | the filter and placebo arms make **no model calls** — they post-process the control arm |
| Optional "prompt" arm | inject "Do not flag: <vetoed files>" into the verifier's prompt instead of filtering; may recover the freed slot; costs one call per task; secondary only, because v1/v2 show prompt injection perturbs |

## 4. Corpus, verifier, pool

| Item | Value | Source |
|---|---|---|
| Corpus, freshness gate, verifier model/serving | as v1 (SWE-bench-Live Python `full`, phase0 run 18; gate 2023-12-31; Llama 3.3 70B via OpenRouter Crusoe→CoreWeave) | v1 |
| Verifier prompt | **v1 file-level, single stage** (`SYSTEM_PROMPT` + `render_prompt`, k = 3) — the prompt the development flags came from; no memory section in any registered arm | v1 D9 |
| Metric (primary) | flag-level false-positive rate at k = 3 (Python-source gold files, non-test) | v1 D18 |
| Metric (guard) | task-level file-level hit@3 | v1 D9 |
| Held-out set | every repo not in {10 treatment, linkding, streamlink, pvlib} with chain ≥ **5** → **60 repos, 759 tasks** (≥ 10 → 34 repos, 581; ≥ 20 → 11 repos, 266); registered choice: **chain ≥ 5** (a veto can form by task 3) | `results/phase0/26/chains.json` |
| Order / seed | chain order per repo; placebo draws seeded (**seed 13**) | this draft |
| Duplicated rows | dropped at load (D37) | D37 |

## 5. Arms

| arm | what it is | calls |
|---|---|---:|
| `control` | v1 file-level verifier, no memory | 1 per task |
| `veto` | control flags filtered by the veto memory (§3) | 0 |
| `placebo` | control flags with the **same number** of flags removed at random from the **same eligible ranks** (seeded) — the memory-free null for a filter | 0 |
| `prompt` (optional, secondary) | verifier re-asked with "Do not flag: …" for tasks with ≥ 1 live veto | ≤ 1 per task |

Two rule variants were developed; **one must be registered**:

| variant | rule | dev: veto vs control | dev: placebo vs control | dev: veto − placebo |
|---|---|---|---|---|
| **P** (rank-1 protected) | drop vetoed flags at ranks 2–3 only | FP −2.13, hit −0.53, precision 0.96 (93 removed) | FP −1.72, hit −1.06, precision 0.91 | FP **−0.41**, hit **+0.53**, precision **+0.043** |
| **U** (unprotected) | drop vetoed flags at any rank | FP −2.69, hit −2.38, precision 0.91 (139 removed) | FP −1.16, hit −5.82, precision 0.81 | FP **−1.53**, hit **+3.44**, precision **+0.101** |

(pts = percentage points; precision = share of removed flags that were
false positives; dev set n = 378 tasks. `phase4/veto_sim.py` and findings §22.)

## 6. Criteria (fixed now)

H3 is supported only if **all** hold on the held-out set, veto vs placebo,
paired by task, bootstrap over tasks (2,000 draws, seed 13):

1. false-positive rate: veto − placebo ≤ −**kill_fp**;
2. hit@3: veto − placebo ≥ 0 (the veto loses no more hits than random removal);
3. precision of removed flags: veto − placebo ≥ **kill_prec**;
4. and veto vs control: hit@3 loss ≤ **guard_hit** (absolute).

Reported, never substituted: veto vs control FP reduction; per-repo table;
number of vetoes formed per repo; the `prompt` arm if run.

Kill numbers follow v2's rule, ceil-to-0.05 of max(MDE, 0.5 × dev effect),
with the MDE from the dev-set bootstrap scaled to the held-out pool (§7):

| variant | kill_fp | kill_prec | guard_hit |
|---|---:|---:|---:|
| P | 0.40 pts | 0.045 | 1.0 pt |
| U | 1.15 pts | 0.075 | 3.0 pts |

## 7. Power (the part that decides whether to run)

Bootstrap SEs of the veto − placebo differences on the dev set, scaled by
√(378 / n) to the held-out pool; MDE = 2.8 × SE (α 0.05 two-sided, power 0.8):

| variant | pool | MDE FP | dev effect | MDE hit | dev effect | MDE precision | dev effect | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| P | 581 (chain ≥ 10) | 0.46 | −0.41 | 0.84 | +0.53 | 0.048 | +0.043 | **underpowered on all three** |
| P | 759 (chain ≥ 5) | 0.39 | −0.41 | 0.73 | +0.53 | 0.042 | +0.043 | borderline on FP and precision, underpowered on hit |
| U | 581 | 1.28 | −1.53 | 2.86 | +3.44 | 0.080 | +0.101 | powered, barely |
| U | 759 | 1.13 | −1.53 | 2.50 | +3.44 | 0.071 | +0.101 | powered |

What this means in plain terms: the *targeting* of the veto is real — on
the dev set it beats matched random removal on every measure, for both
variants — but most of the raw false-positive reduction comes from a fact
that needs no memory at all: **the verifier's rank-2 and rank-3 guesses
are wrong about 9 times in 10**, so dropping any of them helps. The
memory's increment over that is 0.4 FP points (P) or 1.5 (U). Variant U
is the only one a run of this size can test; it buys that testability
with an absolute hit@3 cost of about 2.4 points.

## 8. Harness changes required (none started)

| change | where |
|---|---|
| promotion on `good` records: policy `eligible_labels={"good"}` with file-keyed consolidation; contradiction seam `LabelContradiction` (same file, different labels); supersede on a later `bad` record | `adapters/code/policy.py`, `memkernel` seams (policy settings + one seam class) |
| filter arm and matched random placebo in `RepoPipeline.rolling` (post-processing arms with no model call; per-task record of removed flags and their veto ids) | `adapters/code/pipeline.py` |
| held-out repo selection from `chains.json` (`--held-out-min-chain 5 --exclude <13 repos>`) | `phase4/rolling.py` |
| `phase4.paired` on flag-level FP rate and removed-flag precision with task bootstrap; `phase2.fill_v3` for the kill numbers from the dev bootstrap | `phase4/`, `phase2/` |
| workflow: `stage: rolling` with `arms: control,veto,placebo[,prompt]`, `variant: P|U` | `.github/workflows/experiment.yml` |

About a day; all offline-testable like §3 of v2.

## 9. Owner decision

- **Run variant U on chain ≥ 5** (759 tasks, ≈ 760 control calls plus ≈ 300
  for the optional prompt arm): a genuine, powered, out-of-sample test of
  "memory of one's own mistakes reduces false positives beyond what rank
  alone gives", with a known hit@3 price.
- **Run variant P**: safer for users, but its increment over the placebo is
  inside the noise at any pool the corpus offers; a null would be
  uninformative and a positive would be luck.
- **Do not run; take the product lesson instead.** The finding that
  survives every placebo is about rank, not memory: showing a developer
  fewer pointers, or weighting them by rank, removes most of the false
  positives the veto would. Memory's marginal value on top is measurable
  only with variant U's hit cost.

The recommendation is the third option unless the product specifically
needs *repository-specific* suppression that a global rank rule cannot
give — in which case run U.

## 10. Draft run configuration

`docs/exp-run.v3.draft.json` (variant U, chain ≥ 5, seed 13, arms
control/veto/placebo, prompt arm off). Kill numbers are filled from §6;
nothing else is ⟦FILL⟧.

## Sign-off (unfilled)
- Drafted by: Claude (session), on the owner's instruction, 2026-09-13
- Approved by owner: ______ · Registered commit / tag `prereg-v3`: ______
