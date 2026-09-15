# Memory Value Report — rcolkitt/vasperamemory

**Status: exploratory, not registered.** One product repository, 46 tasks from 60 commits, 36 scored. Nothing here changes the registered v1/v2 verdicts. Numbers are exact; conclusions are labelled as strong or weak.

Run: `results/experiment/23/` (branch `run/exp-vm-report2`, workflow run 23). Corpus: `reports/vasperamemory/history/` built by `phase0/repo_corpus.py` from the local clone at `5cf2416` (main, 2026-09-15). Arms: control, treatment (ungated file-level memory, τ = 0), placebo (matched count of irrelevant memories from `docs/placebo-pool.v2.json`). Design: prequential (rolling), warm-up 10, seed 17. Analysis: `python -m phase4.memory_value`, `python -m phase4.veto_sim --dirs results/experiment/23/rolling --level file`.

## 1. The answer in four lines

1. **Your history is unusually repetitive.** Two thirds of changes land in a file already changed in the window; nine files take 38% of all hits. That is the precondition for memory to matter, and it is met.
2. **A localizer with no memory already finds the file 97% of the time**, with the right file at rank 1 on 33 of 36 tasks, because your commit messages name the paths (full gold path in 20 of 36 scored messages, a gold file name in 26). On this corpus there is nothing left for memory to add.
3. **Injected memory did not add anything, and behaved exactly like the placebo**: both lost the same one task, both raised false positives by 1.5 points, and the treatment's flags matched the placebo's on 20 of 36 tasks. This is the third time in this project that a placebo arm has explained the treatment arm.
4. **The value in this data is not in the localizer prompt.** It is in the change prior, co-change map, and source→test map that `git_commits` already holds and nothing consumes (§4–§5). Six gaps, ranked, with the number from your own history that motivates each.

## 2. What your history says (offline, no model calls)

Source: the last 60 commits on `main` of rcolkitt/vasperamemory (2026-07-09 to 2026-09-15), read from a local clone by `phase0/repo_corpus.py`. A commit becomes a task when it has a parent, a message of at least 60 words, and a diff touching at least one non-test source file (`.ts .tsx .js .mjs .py`). The commit message is the "problem statement"; the source files it changed are the gold answer.

| Quantity | Value |
|---|---|
| Commits scanned | 60 |
| Usable tasks | 46 |
| Dropped: no source file changed (docs, config, migrations only) | 13 |
| Dropped: root commit | 1 |
| Commit type | fix 25, feat 16, other 5 |
| Gold files per task | median 2, max 36; 8 tasks touch more than 5 files |
| Median tree size at the commit | 421 source files |
| Median message length | 183 words (min 63) |
| Source commits that also change tests | 24 of 46 (52%) |
| Commits touching `supabase/migrations/` | 10 of 60 |

### 2.1 Recurrence: does the past predict where the next change lands?

This is the number that decides whether *any* memory of prior changes can help a localizer on this repo. A task is "recurring" when at least one of its gold files was already a gold file in an earlier task.

| Window | File level | Directory level |
|---|---|---|
| All 46 tasks | 31 / 46 (67%) | — |
| After a 10-task warm-up (36 scored tasks) | 24 / 36 (67%) | 30 / 36 (83%) |
| Same, but the file must have been hit **≥ 3 times** before (`seen3`) | 14 / 36 (39%) | — |
| `fix` commits only | 19 / 25 (76%) | — |

Two thirds of changes, and three quarters of bug fixes, land in a file that has already been changed in the window. For comparison with the public Python repos of the registered experiments (findings §10, build prefix 20): VasperaMemory's `seen3` after 20 tasks is 0.50, against a median of about 0.29 across the 13 public repos (range 0.00 to 0.95). Your codebase is *more* repetitive than the average open-source project, because it is young, single-author, and has a few load-bearing files. That is the precondition for a memory of prior changes to be worth anything at all.

### 2.2 Hotspots

123 distinct files carried a change; 28 were hit at least twice and 9 at least three times. The top of the list is where a localizer's prior belongs:

| File | Times changed (of 46 tasks) |
|---|---|
| `server/index.ts` | 7 |
| `server/mcp-sse.ts` | 7 |
| `packages/cli/src/cli.ts` | 7 |
| `lib/subscription.ts` | 6 |
| `app/api/auth/register-repo/route.ts` | 5 |
| `lib/projects.ts` | 5 |
| `app/admin/layout.tsx` | 4 |
| `lib/identity.ts` | 3 |
| `server/tools/decision-tools.ts` | 3 |

By directory: `lib/` 17, `server/` 16, `packages/cli/src/` 10, `app/api/auth/register-repo/` 5, `lib/governance/` 5.

### 2.3 Co-change: files that move together

Pairs that changed together in at least two tasks (broad refactors excluded):

| Pair | Tasks |
|---|---|
| `app/api/auth/register-repo/route.ts` + `lib/projects.ts` | 3 |
| `register-repo/route.ts` + `lib/identity.ts` | 2 |
| `register-repo/route.ts` + `lib/memory-service.ts` | 2 |
| `register-repo/route.ts` + `lib/subscription.ts` | 2 |
| `lib/memory-service.ts` + `lib/projects.ts` | 2 |
| `lib/projects.ts` + `lib/subscription.ts` | 2 |
| `packages/cli/src/cli.ts` + `packages/cli/src/context.ts` | 2 |
| `packages/cli/src/cli.ts` + `server/governance-routes.ts` | 2 |
| `lib/governance/conflict-checker.ts` + `lib/governance/gate-service.ts` | 2 |

The register-repo route is a hub: every time it changes, one of four `lib/` files changes with it. The CLI and the server's governance routes are coupled across a package boundary, which is exactly the kind of coupling an agent working in `packages/cli/` cannot see from the file tree.

### 2.4 Breadth

Eight tasks touched more than five files. One of them (36 files, 31 of them under `attic/`) is a bulk move that no localizer can predict and that also pollutes any naive "files changed recently" signal. The others are 6 to 15 file cross-layer changes (`app/` + `lib/` + `server/` together), which is the shape of a feature that adds an API route, a service function and a tool at once.

## 3. What the model run says (36 scored tasks, file level)

### 3.1 Arms

| Arm | hit@3 | FP rate | flags / task | memory retrieved | vs control (paired) |
|---|---|---|---|---|---|
| control (no memory) | **0.972** (35/36) | 0.341 | 2.53 | — | — |
| treatment (file memory, τ = 0) | 0.944 (34/36) | 0.356 | 2.50 | 36 / 36 tasks | 0 wins, 1 loss, −2.8 pts |
| placebo (irrelevant memory, same count) | 0.944 (34/36) | 0.356 | 2.50 | 36 / 36 tasks | 0 wins, 1 loss, −2.8 pts |

Treatment − placebo: 0.0 pts. The task both arms lost and control found was `7c7af24bfc` (gold `lib/governance/ledger-service.ts`, both memory arms answered `packages/cli/src/governance/ledger.ts`). The treatment's flag list was identical to the placebo's on 20 tasks and to the control's on 18; the placebo matched control on 26. In other words, *adding any text to the prompt* moved the output more than *what the text said*. The memory store held 13 promoted locations by the end (`server/governance-routes.ts`, `lib/governance/gate-service.ts`, `lib/identity.ts`, `server/tools/decision-tools.ts`, …), all genuinely from your history, and none of them helped.

Gate 4 as computed by the harness: lift −2.78 pts, FP rise +1.49 pts, no effect in the majority of repos (there is one repo). Not a registered gate; reported for the record.

**Strength of this conclusion: strong for "memory does not help here", for a boring reason: control is at ceiling.** With one miss in 36 there is no room to measure lift. Do not read the −2.8 as "memory hurts" either; it is one task.

### 3.2 Why control is at ceiling: the messages name the files

| Of the 36 scored tasks, the commit message contains… | Tasks |
|---|---|
| the full path of a gold file | 20 |
| the file name of a gold file | 26 |
| the directory name of a gold file (all 46 tasks) | 39 / 46 |

Your commit messages are 183 words at the median, written by coding agents, and they say what changed and where. That is a very different input from the bug reports in the registered experiments (median control hit@3 there: 0.55 to 0.80). Even on the 10 tasks whose message names no gold file, control found a gold file 9 times, at rank 1 — because the message names the feature, and the feature lives in one obvious place in a 421-file tree.

**What this means for the product:** on a repository with disciplined, agent-written commit messages, the commit log *is* the memory. Plain retrieval over `git_commits.message` → `files_changed` would answer "where did we handle X before" with no model call and with provenance for free. That is the cheapest feature in §5 and the one this run most directly supports.

### 3.3 Precision by rank (control)

| Rank | Correct | Shown | Precision |
|---|---|---|---|
| 1 | 33 | 36 | **0.92** |
| 2 | 19 | 32 | 0.59 |
| 3 | 8 | 23 | 0.35 |

First correct pointer at rank 1: 33 tasks; rank 2: 2; never: 1. Compare the cross-repo profile in `docs/PRODUCT-LESSON-rank.md` (0.49 / 0.15 / 0.13 on 526 tasks). Your repo is easier at every rank, and the rank-1 to rank-2 drop is the same shape.

Display policy on this repo:

| Show top-k | Hit rate | Wrong pointers per task |
|---|---|---|
| 1 | 0.917 | 0.08 |
| 2 | 0.972 | 0.44 |
| 3 | 0.972 | 0.86 |

Showing the second pointer buys 2 tasks out of 36 and costs 0.36 wrong pointers per task; the third buys nothing and costs another 0.42. The rank lesson holds here with a much sharper edge: **show one**.

### 3.4 Veto memory, simulated

`phase4.veto_sim`, k = 2, file level: 0 flags removed, hit@3 unchanged, FP rate unchanged. The control repeated a false positive on only four files (`lib/utils.ts`, `server/mcp-ai-learning.ts` twice each with no true positive; `gate-service.ts` and `ledger-service.ts` twice each but also correct at other times), and never a third time within the window. Veto has nothing to bite on in 36 tasks. Weak conclusion; window too short.

### 3.5 Recurrence and the control

Control hit on tasks whose gold file had already been a gold file: 20 / 20. On tasks with an entirely new gold file: 15 / 16. So the control did not need recurrence either; it needed the message.

## 4. What VasperaMemory has today, checked against the numbers

This is a read of the current `main`, not the marketing page. Each row says what exists, whether it is wired to a live path, and what the history above says it should be doing.

| Capability | Where | State | Verdict |
|---|---|---|---|
| Commit ingestion | `packages/cli/src/git-hooks.ts` post-commit → `POST /api/activity` → `git_commits` table (hash, message, `files_changed[]`, insertions, deletions) | **Live.** Every hook-installed commit lands in the table. | The raw material for every recommendation below is already being collected. Nothing consumes it for localization. |
| Hotspot detection | `packages/cli/src/local-intelligence.ts` `getFrequentlyChangedFiles(days, limit)` | Local mode only (SQLite CLI). Feeds `summary.hotspots` and evolution patterns. | Correct idea, wrong window: "last 30 days" rather than "last N tasks", and never surfaced as a ranked prior to the agent when it is asked to find a bug. |
| Co-change detection | `lib/timeline-builder.ts` `findCoChangedEntities` (hosted), `local-intelligence.ts` `findCoChangedFiles`, `local-server.ts` `analyzeGitCoChanges` (only reports a count inside `what_changed`) | Hosted version has **no callers**. Local version only reports a count. | The history shows real coupling (register-repo route ↔ four `lib/` files; CLI ↔ governance routes). This is the single most useful thing the data can say and it is unwired. |
| Change risk | `estimate_change_risk` in `server/mcp-sse.ts` | Live, but scores from hand-written regexes (`/auth\|login/`, `/mcp\|sse\|server/`) and a list of **VasperaMemory's own filenames** (`mcp-sse.ts`, `db-supabase.ts`). | Not measured, and not portable: a customer's repo gets your file names as "critical". Replace the weights with the customer's own churn and co-change counts from `git_commits`. |
| File context | `get_file_context` → `file_context` table + `get_file_context_full` RPC | Live query path, but nothing in `lib/`, `server/` or `app/` writes to `file_context`. | Reads an empty table on every fresh project. Populate it from `git_commits` (last change, change count, co-changed files) and the tool becomes useful without new capture. |
| Error → fix memory | `errors action:capture/search` → `error_fix_chains` (`find_error_fix` / `capture_error_fix` deprecated aliases) | Live. | Right shape for a *veto/prior* memory, but keyed on error message only. Add the files touched by the fix; then "this error was fixed in `lib/subscription.ts` last time" is retrievable. |
| Governed memory (Gate + ledger) | `lib/governance/` | Live for proposed writes. | The right place for a hotspot memory to *land* so it carries provenance ("promoted from 7 commits, last 2026-09-12"). Do not bolt a side store on. |

## 5. Gaps, in priority order

Each gap has a number from your own history attached, so you can check the claim rather than trust it.

### Gap 1 — The agent is never told where changes usually land

**Evidence.** 67% of tasks (76% of fixes) touch a file already changed in the window; 9 files account for 47 of 123 gold hits. The control localizer, with no memory, finds a gold file in the top 3 on 35 of 36 (97%), with the correct file at rank 1 on 33 of 36 of tasks.

**What to build.** A *change prior*: a per-project ranked list of files by recent change count and co-change strength, computed from `git_commits`, promoted into the Domain/System pillar through the Gate (so it has provenance and can be vetoed), and returned by a single tool call (`where_do_changes_land` or folded into `get_codebase_summary`). One call, top 5, with the count next to each file, so the agent can weigh it. This is a 100-line SQL view plus one tool; the ingestion already runs.

**What not to build.** Do not inject the prior into the localization prompt as free text. Two registered experiments (v1, v2) and a placebo arm showed that injected prior-defect memories do not raise hit@3 and slightly raise false positives. Give the agent the list as data it can consult, not as a hint that biases its reading.

### Gap 2 — Coupling across packages is invisible

**Evidence.** `packages/cli/src/cli.ts` co-changed with `server/governance-routes.ts` in 2 of 7 CLI tasks. The register-repo route co-changed with `lib/projects.ts` 3 times and with three other `lib/` files twice each. An agent editing one side of these pairs has no signal that the other side usually moves too.

**What to build.** Wire `findCoChangedEntities` (already written, zero callers) into `analyze_change_impact` and `estimate_change_risk`: "files that changed with this one in ≥ 2 of the last 50 commits". This is the checklist an agent can act on immediately (open the coupled file, look for the parallel change). It is also the one feature here that helps *writing* code, not only locating bugs.

### Gap 3 — Risk scoring is hard-coded to your own repo

**Evidence.** `estimate_change_risk` adds 40 points for any file named `mcp-sse.ts` and 35 for `db-supabase.ts`. Those names are yours. On a customer's repo the score is regex noise.

**What to build.** Replace the fixed weights with measured ones: churn rank from `git_commits`, co-change fan-out, and whether the file has an `error_fix_chains` entry. Keep the regex list only as a fallback for a project with fewer than ~20 commits ingested. Show the evidence next to the score ("changed 7× in 60 commits; coupled to 4 files"), which CONSTITUTION.md's "displayed stats must be literally true" rule already requires.

### Gap 4 — Ranked pointers are shown as a flat list

**Evidence (cross-repo, `docs/PRODUCT-LESSON-rank.md`).** Rank-1 file precision 0.49, rank-2 0.15, rank-3 0.13 on 526 tasks. On your repo: rank-1 0.92, rank-2 0.59, rank-3 0.35 (36 tasks; see §3.2). When a wrong pointer costs the developer more than about a tenth of a right one, showing one pointer beats showing three.

**What to build.** Anywhere VasperaMemory surfaces "likely files" (file context, error-fix search, the dashboard), show rank 1 with confidence and collapse ranks 2 to 3 behind a "more" affordance. Record which pointer the user opened; that click log becomes the calibration set the next version needs.

### Gap 5 — Half of source changes ship with a test change, and the memory does not know which test

**Evidence.** 24 of 46 source-changing commits also touched a test file. The corpus builder had to strip tests to score, but as product data it is a gift: "when `lib/subscription.ts` changes, `__tests__/subscription.test.ts` changes 4 times out of 6".

**What to build.** A source→test co-change map (same query as Gap 2, restricted to test paths), surfaced when an agent edits a source file: "run and probably update these tests". Cheap, and it turns a memory feature into a CI-time-saver, which is easier to sell than "better localization".

### Gap 6 — Non-source commits are noise in every current signal

**Evidence.** 13 of 60 commits touched no source file (docs, config, migrations), and one 36-file `attic/` move would dominate any "recently changed" list.

**What to build.** Classify commits at ingestion (source / test / migration / docs / bulk-move, where bulk-move is > 20 files with > 80% renames) and let every consumer filter. Migrations deserve their own memory: 10 of 60 commits touched `supabase/migrations/`, and "which migration last changed this table" is a question agents ask constantly.

## 6. What this does *not* say

- It does not say memory injected into the localizer's prompt will help on your repo. The registered result across 13 public repos was a null-to-negative effect, twice, with the placebo capturing most of any movement. The exploratory run below is 36 evaluation tasks; treat its arm deltas as noise unless they are large.
- It does not measure the write-side (does the agent produce a *better fix*). Only where-to-look.
- The sample is 60 commits. Re-run this report at 200 commits; the recurrence and hotspot numbers will move, and the `attic/` move will fall out of the window.

## 7. Reproduce

```
# corpus (needs a local clone of the product repo)
python -m phase0.repo_corpus --clone /path/to/VasperaMemory --repo rcolkitt/vasperamemory \
    --out reports/vasperamemory/history --suffixes .ts,.tsx,.js,.mjs,.py
# run: push a run/* branch whose .exp-run.json has
#   stage=rolling, corpus_path=reports/vasperamemory/history, file_lists=true,
#   source_suffixes=.ts,.tsx,.js,.mjs,.py, arms=control,treatment:0,placebo:0, warmup=10, seed=17
# read-out
python -m phase4.memory_value results/experiment/23/rolling/rcolkitt__vasperamemory.arms.json
python -m phase4.veto_sim --dirs results/experiment/23/rolling --level file --k 2
```

Privacy: the run branch carries commit messages, source diffs and file listings of the product repo; the model provider saw messages and file paths (no source). The branch is in a private repository.
