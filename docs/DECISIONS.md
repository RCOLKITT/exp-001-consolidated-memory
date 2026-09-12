# Decision log

Open decisions from spec §9 plus design decisions made while building the
kernel. Each entry: what was decided, why, and what it forecloses.

## Open (spec §9)
1. **Primary corpus** — ChainSWE vs SWE-bench-Live. Resolve in Phase 0 by
   measuring per-repo chain length (`python -m phase0.chains`). Known so far:
   ChainSWE is 304 issues across 54 Python repos mined from six SWE-bench-family
   sets, i.e. ~5.6 issues per chain on average, which is far below any
   plausible build+eval split. SWE-bench-Live (Python) `full` adds ~50 verified
   issues per month across its repos. Expect the answer to be "SWE-bench-Live
   full, restricted to the few repos with long chains", and expect Gate 2 to
   bite on chain length. Its dataset could not be pulled from the cloud
   session (huggingface.co blocked), so the report is produced by the runbook.
2. **Retrieval index** — reuse VasperaMemory's or stand up a separate one.
   Leaning separate: Gate 1 determinism requires a cache keyed by content
   hash with a pinned embedding model, which is easier to guarantee in
   isolation.
3. **Positioning** — kernel as a promotion of VasperaMemory, or a new
   component that consumes it as storage. Make the call before Phase 3.
4. **Power calculation inputs** — needs the Phase 0 baseline.

## Decided while building the kernel

### D1. Language: Python
SWE-bench-Live tooling, Docker orchestration, and embedding clients are all
Python-first. The kernel is dependency-free so it can be ported to
TypeScript later if decision 3 says the kernel *is* VasperaMemory.

### D2. Redundancy reinforces; it is not discarded
At Θ_surprise = 0.35, a repeat of a buffered pattern is (correctly) not
written as a new entry. But the promotion policy (§6.1) needs
`occurrence_count >= 3` *distinct source records*. If repeats were dropped,
promotion could never fire — the first synthetic run proved this (zero
promotions on a stream with 50% injected redundancy). So a redundant
candidate whose nearest neighbour is a **buffered** entry is attached to
that entry as supporting evidence (`BufferEntry.support`). It counts toward
occurrences, distinct inputs, and separation of duties, and lands in the
promoted memory's provenance. The Gate 3 metric ("discarded as redundant")
still counts these: they are not new writes. A candidate redundant to
already-**promoted** memory is discarded outright and logged with the
memory id it matched, which is exactly the retrieval-hit-rate signal.

### D3. Wall clock is excluded from every hash
Memory ids and ledger hashes cover causal tokens and content, never wall
clock. Consequence: a replay run on a different day produces a
byte-identical ledger chain (`tests/test_replay.py`). Wall clock is still
recorded on every object and ledger entry for humans.

### D4. TTL is in kernel ticks, not seconds
Same reason as D3: expiry must be deterministic under replay. In Phase 3 one
tick is one nightly run.

### D5. Promotion runs on the tick schedule, never on ingest
`PromotionPolicy.schedule_every_ticks`. `Kernel.promote()` exists for tests
and manual runs and is refused once frozen.

### D6. Clustering is greedy single-pass by similarity to the cluster seed
Deterministic given buffer insertion order. Good enough for Phase 1; if
Phase 3 shows fragmented clusters, revisit — but only before
pre-registration.

### D7. Versions are snapshots of live ids, not views
`store.freeze()` records the exact set of live object ids under a digest.
`store.at(v)` returns that set forever, even after later supersessions.
`at(None)` returns nothing: this is the control arm.

### D8. Phase 0 localization runs on git checkouts, not Docker images
File-level localization needs the source tree at `base_commit` and nothing
else: no dependency install, no test execution. `run_control` clones each
repo once and checks out per task. Docker images (`Task.docker_image`, the
`starryzhang/sweb.eval.x86_64.*` namespace) and time-machine pinning
(`phase0/timemachine.py`) are wired but only exercised when execution-based
checks are needed (Gate 2 oracle hand-check, or a later line-level metric).
This keeps Phase 0 runnable on a laptop with git, HF access, and a model key.

### D9. Localization metric is task-level hit@k over files, paired with flag-level FP
- A task is "localized" if any of its top-k flagged files overlaps a gold
  hunk in a non-test file.
- FP rate is over flags: flagged files with no gold overlap / all flags.
- k is fixed for the whole experiment (default 3) and pre-registered.
- Test files are excluded from ground truth; a verifier that names the test
  is not localizing the defect.
Rationale: file-level is what published baselines report; the paired FP
metric is what stops threshold games (§8). Line-level is a later refinement
and would need Docker (D8).

### D10. Published baseline reference is a pre-registration value, not a memory
arXiv and the SWE-bench-Live leaderboard were unreachable from the cloud
session, so no number is recorded here. Do not fill Gate 0 from recollection.
Candidates to read and pin: the Agentless paper's localization tables
(arXiv 2407.01489) and the SWE-bench-Live leaderboard. Record metric
definition, k, model, and corpus alongside the number.

### D11. Determinism is a cache property, not a sampling property
Model sampling is not reproducible. The harness content-addresses every
request (sha256 of model, system, user prompt, schema, effort) and stores the
response; `--offline` reruns fail on any miss. "Identical results on identical
inputs" (Gate 0.3) is therefore a claim about the harness, and the manifest
records cache hits/misses so a reviewer can see it.

### D12. A memory is `symptom => location :: reason`
First draft excluded the issue text from memory content so memory would
capture "where defects live, not what issues say". The first end-to-end test
showed why that cannot work: retrieval is keyed by the new issue's text, and
a location-only memory shares no tokens with it, so the treatment arm never
retrieved anything. A defect pattern that can be *recalled* must pair the
symptom (the issue's first line, i.e. its title) with the location. The
surprise gate still de-duplicates on the whole string, so repeated
symptom+location pairs reinforce rather than re-write.

### D13. Learning consults memory as it grows
During Phase 3 the verifier retrieves from the latest promoted snapshot
(`snapshot()` + `pin()` after every promotion that adds memory). This is the
"treatment pipeline" of the spec; it also means the build split produces
retrieval ledger entries that show when memory first became usable.

### D14. Similarity seam is still the Jaccard placeholder
`phase3/learn.py::similarity()` returns TokenJaccardSimilarity. Phase 2
replaces it with `EmbeddingCosineSimilarity` over a pinned embedding model
with a content-hash cache (adapters/code/similarity.py). Θ_surprise and
`cluster_similarity` must be re-tuned on synthetic streams for that seam
before pre-registration; the Jaccard values do not transfer.

### D15. Stated model cutoffs (pre-registration input, from the vendor page)
Source: https://platform.claude.com/docs/en/models/overview (read 2026-09-09).

| Model | Training data cutoff | Reliable knowledge cutoff |
|---|---|---|
| claude-fable-5-1 | Jun 2026 | Jun 2026 |
| claude-opus-5 | May 2026 | May 2026 |
| claude-sonnet-5 | Jan 2026 | Jan 2026 |
| claude-haiku-4-5 | Jul 2025 | Feb 2025 |

The freshness gate uses the **training data** cutoff (the broader range),
taken as the last day of the stated month. For `models.json` that is
`{"claude-opus-5": "2026-05-31"}`.

Consequence, from `results/phase0/2/corpus-summary.json`: the Python
SWE-bench-Live `full` split runs 2021-07-22 → 2025-09-02. **No task in it
postdates any Claude 5 model's cutoff.** Options, in order of preference:
1. A corpus with 2026 tasks — SWE-bench-Live/MultiLang was refreshed
   2026-08-21 per its README (run 4 measures its date range and chains).
2. Evaluate a model whose cutoff precedes the corpus — only Haiku 4.5
   (Jul 2025) qualifies, leaving August 2025 tasks at most; chains would be
   far too short for Gate 2.
3. Build fresh tasks ourselves from the long-chain repos' 2025-09 → now
   issue history with the SWE-bench-Live curation pipeline (RepoLaunch),
   which the corpus decision (§9.1) never anticipated and which costs Phase 0
   its "4 days".
Never weaken the gate to fit the corpus (§8, contamination).

### D16. Option A chosen: choose the model to fit the freshness gate
Owner decision (2026-09-10). The corpus stays SWE-bench-Live (Python,
`full`); the verifier model must have a vendor-documented training cutoff
early enough to leave long chains. Candidates checked against primary
sources:

| Model | Stated cutoff (source) | Still served? | Gated corpus (run) |
|---|---|---|---|
| Llama 3.3 70B Instruct | "Data freshness: December 2023" (meta-llama/llama-models MODEL_CARD.md) | open weights; Together/Fireworks/Groq/Bedrock | run 7, gate 2023-12-31 |
| Llama 4 Maverick / Scout | "Knowledge cutoff: August 2024" (llama4 MODEL_CARD.md) | open weights; same hosts | run 8, gate 2024-08-31 |
| Claude Sonnet 4 / Opus 4 | not verified (model page 404; deprecated) — believed Mar 2025 | deprecated, retirement TBD | run 9, gate 2025-03-31 |
| Claude Sonnet 4.5 | training data cutoff Jul 2025 (model page) | active (legacy) | too late |
| Claude 3.x (Apr 2024 and earlier) | — | **retired** | — |

Meta documents one date ("knowledge cutoff"), not a separate training-data
date; the gate uses it as written and the pre-registration records the
wording. Access is through the `openai-compatible` provider in
`phase0/verifier.py` (chat-completions, `response_format` json_schema with
fallbacks, temperature 0). The cache remains the determinism mechanism (D11).

Measured (runs 7, 10): the August 2024 gate keeps 4 eligible repos, the
December 2023 gate keeps 13. Recommendation is therefore **Llama 3.3 70B**,
with Llama 4 Maverick pre-registered as the fallback (docs/phase0-findings.md §6). Localization level will be below Opus 5; the
experiment measures lift, and Gate 0 compares against a baseline reported
for a comparable model, not a frontier one.

### D17. Verifier pinned to one OpenRouter endpoint
`results/phase0/11/control/endpoints.json` lists 13 hosts serving
`meta-llama/llama-3.3-70b-instruct` behind OpenRouter, at quantisations
fp8, bf16, fp16 and "unknown", with context windows from 12k to 131k. A
quantised or context-truncated build is a different verifier, and unpinned
routing can switch between them mid-run. The pre-registered verifier is
therefore the **Crusoe bf16 endpoint** (131,072 context, structured
outputs supported, $0.25 / $0.75 per M tokens at the time of listing), via
`model_extra = {"provider": {"order": ["Crusoe"], "allow_fallbacks": false}}`.
Fallback if Crusoe is unavailable during a run: CoreWeave fp16 (128k,
structured outputs), recorded as a deviation if used. Never fp8 for
pre-registered runs.

### D18. False-positive rate is a paired metric, not a level
With k flags per task and g gold files (g is usually 1), the flag-level FP
rate cannot go below (k - g) / k, i.e. ~0.67 at k = 3. Run 17's 0.88 sits
above that floor by 0.21, which is the interpretable part. Gate 4 compares
the two arms' FP rates at the same k on the same tasks, so the floor
cancels. Report the level alongside precision@1 in Phase 4 so readers can
see the floor; do not "fix" the metric after seeing data (§7).

### D19. Verifier definition includes the ordered fallback; ceiling rule to be pre-registered
Run 18 showed the single-provider pin (D17) is not operationally stable:
21% of requests fell through to CoreWeave under Crusoe rate limits. The
verifier is redefined as the ordered pair Crusoe bf16 → CoreWeave fp16
with `allow_fallbacks: false` (no third provider, no quantised build), and
`served_by` is recorded per request. A run where any request is served by
another provider is invalid.

Separately, two of the 13 draft repos sit at ≥ 0.95 control hit@3. Whether
to exclude repos at the ceiling is a pre-registration decision (findings
§8, options a–c); it must be fixed before Phase 3 and justified only with
Phase 0 control data.

### D20. Similarity seam: pinned sentence-transformers model, vectors saved with the run
`adapters/code/similarity.py` now has three seams: Jaccard (Phase 1 placeholder),
a feature-hashing embedder (no model; used by tests and to sanity-check the
sweep anywhere), and `sentence-transformers/all-MiniLM-L6-v2` pinned to a Hub
commit sha resolved and recorded by the phase2 workflow. Vectors are cached
by sha256(embedder name + text) in `embeddings.jsonl` next to the run's
response cache, so replay never re-embeds. Θ_surprise and cluster_similarity
for the embedding seam come from `phase2.tune` on synthetic streams (D14);
the Jaccard defaults do not transfer. The embedding model never sees gold
patches or produces flags, so it is outside the freshness gate's scope.

### D21. Synthetic streams for semantic seams must be natural language
Phase 2 run 1 swept Θ with the pinned MiniLM model on the Phase 1 token
streams (`p12t3 …`): no cell reached discard ≈ injected with pure
promotions, because a sentence embedder cannot separate one gibberish
pattern from another (purity ≤ 0.2 at any Θ that discards enough). That is
a property of the test stream, not the seam. `memkernel.synthetic` now has
an `nl` mode: a pattern is (component, symptom) rendered as paraphrased
defect sentences with prefix/suffix noise, 450 distinct patterns. Gate 1's
discard assertion for the embedding seam is evaluated on `nl` streams; the
token streams remain for lexical seams.

### D22. Reinforcement has its own threshold (ρ), separate from admission (Θ)
Phase 2 run 3 (pinned MiniLM, natural-language streams): at every Θ that
discards the injected 70% of redundancy, promoted memories were almost
never pure (≤ 0.05) — paraphrases of two different symptoms in the same
component sit closer in embedding space than the admission bar. One
threshold cannot separate "same defect" from "same component". The kernel
now takes `reinforce_min_sim` (ρ): a non-admitted candidate reinforces its
nearest buffered entry only if similarity ≥ ρ, otherwise it is discarded
without becoming evidence. ρ = None keeps the old behaviour (ρ = 1 − Θ).
The sweep reports purity at pattern and at component level, because for
localization a merge within one component mostly points at the same
files; the pre-registration must state which purity it commits to.

### D23. Seam operating point: Θ = 0.45, ρ = 0.70, cluster = 0.60 (MiniLM @ 1110a243)
Pairwise cosines on the natural-language stream (phase2 run 4 vectors,
400 records, 120 patterns): same-defect paraphrases median 0.52 (p25 0.38);
same component, other symptom median 0.41 (p75 0.57); different component
median 0.19 (p95 0.42). The first two overlap heavily, so no threshold
separates "same defect" from "same component" — pattern-level purity stays
≈ 0.3 everywhere. Different components are well separated, and component
purity reaches 0.94 at Θ 0.45 / ρ 0.70 / cluster ≥ 0.60 with discard 0.75
on a 70%-redundant stream and 17 promotions from 400 candidates. Above
cluster 0.60 nothing changes: promotions come from reinforced entries, not
from clustering separate entries.

Consequence for the code adapter: the unit memory consolidates is the
component, which in real records carries the file path — the thing
localization needs. The pre-registration commits to component-level purity
(≥ 0.90 on the synthetic check) and to these three constants; Gate 3's
"> 60% discard" is consistent with this regime.

### D24. Code adapter consolidates by file; retrieval stays semantic
Real-data diagnostics (experiment run 3: pvlib, pdm, haystack, 20 build
tasks each, `results/experiment/3/learn/*.diagnose.json`): same-file record
pairs have median cosine 0.59–0.64 and different-file pairs 0.37–0.47 under
the pinned MiniLM seam, with heavy overlap; at Θ 0.45 / ρ 0.70 between 16
and 30 of ~60 records per repo fell in the "neither admitted nor
reinforced" band and were lost, and nothing promoted although 1–3 files
per repo were true defect locations ≥ 3 times. Reinforcement also went
mostly to false-positive flags (pvlib: 25 good vs 4 bad), which the
label-eligibility rule (§6.5) correctly kept out of memory.

Decision: the seam is split. **Consolidation** (surprise gate,
reinforcement, promotion clustering) uses `FileKeyedSimilarity`: same file
⇒ 1.0, different file ⇒ 0.0, so the unit of memory is the file — the
"component" D23 already identified — and purity is 1.0 by construction.
**Retrieval** uses the pinned embedding cosine between the new issue's
text and each memory's `symptom => file :: reason` content, so what is
recalled is chosen semantically. Θ and ρ then govern only the synthetic
Gate 1 checks and the embedding-consolidation variant, which remains
available (`--consolidation embedding`) as the comparison condition.
Promotion still requires three `bad` records from three distinct tasks.

What this makes the treatment arm: a consolidated, provenance-tracked
prior over recurring defect locations, recalled by symptom. Whether that
lifts localization is exactly the efficacy question; the recurrence
report (`results/phase0/20/recurrence.md`) bounds how much it could.

### D25. Registered design (prereg-v1)
Owner approved the recommended design and ceiling option (b) on
2026-09-10. Promotion at ≥ 2 records from ≥ 2 tasks (spec §6 said 3):
the recurrence analysis (findings §10–11) showed that at 3 the maximum
possible lift is below the detectable effect in every split, so the
experiment could not have returned a positive result by construction.
Build split by chain length, ceiling rule at 0.90 control hit@3
(excludes streamlink, pvlib), linkding as negative control, kill number
10 pts against a ceiling of ~17.9 and an MDE of ~9.2 on 373 eval tasks.
All values in docs/PREREGISTRATION.md; run config in docs/exp-run.prereg.json.
Nothing here changes after the tag.

### D26. Gate 0.1 closed with a recomputed reference, not a quoted one
The published baseline is Agentless's file-level localization, recomputed
from the authors' released `loc_outputs.jsonl` with our own metric code
against SWE-bench Lite gold (findings §13). This is stronger than quoting
a table because the metric definition is provably identical; it is weaker
in that model and corpus differ from ours, which is stated. The
pre-registration is unaffected (§7 lists no baseline value).

### D27. Gate 2.3 oracle hand-check: how it was closed
The spec asks for manual labels on 50 flags with ≥ 95% agreement. The
owner delegated the review. Two checks stand in for the human read, both
recorded: (1) a row-by-row audit of `results/phase0/19/control/handcheck.csv`
confirming every oracle label equals "flagged file ∈ gold files" and that
no gold list contains a test file; (2) an independent patch parser
(`phase2.handcheck verify`, `+++ b/` lines, separate test-path rule)
re-deriving the gold files on the runner: 50/50 agreement and identical
gold sets on every row (`results/phase0/22/control/handcheck-verify.txt`).
The oracle is a deterministic file-overlap rule, so its only failure mode
is gold extraction, which (2) tests directly. The owner may repeat the
manual read at any time; the file is unchanged.

### D28. Gate 3 failures do not change the primary analysis
Run 5 (registered) passed Gate 3 on 7 of 10 treatment repos; conan, keras
and sphinx fell below the registered floors (findings §14). The
pre-registration set the floors but did not say what to do with a repo
that misses them, so the rule is fixed here, before any Gate 4 number
beyond the already-seen conan arm was read: the primary result is the
registered aggregate over all 10 treatment repos against the 10-pt kill
number; the 7-repo passed-Gate-3 subset is reported alongside as a
labeled secondary, never substituted for the primary. Dropping repos
whose memory failed to form would select on the mechanism working and
bias the headline upward; keeping them reports what the design as
registered actually delivers.

### D29. Resume, don't re-learn, after the truncated-JSON abort
Run 5's evaluation aborted on cfn-lint when the verifier returned
truncated JSON. The fix salvages the ordered path list from truncated
output and drops a task whose call still fails from both arms (pairing
preserved, count recorded in `arms.json: errors`). Run 6 resumes at
`stage = evaluate` from run 5's kernels and caches (`learn_run = 5`,
`resume.json`), so the frozen memory versions evaluated are the ones run
5 produced; the run 5 conan arm is reproduced from cache, not re-sampled.

### D30. Verdict on the registered run: killed, reported as registered
Gate 4 on runs 6/7 (findings §15): lift +1.08 pts on 371 paired tasks,
95% CI −2.0 to +4.2, against a registered kill number of 10; majority
criterion fails (3/10 repos positive); FP ceiling and negative control
pass. The result is reported exactly as the pre-registration defined it —
primary aggregate over all 10 treatment repos, kill number 10, no
subsetting. The passed-Gate-3 secondary (−0.45 pts) is reported beside
it and points the same way. No thresholds were re-tuned after the data
were seen and no further registered runs were spent. The experiment's
thesis ("memory of prior defects improves localization without inflating
false positives, every belief traceable") is answered on its first
clause: at file granularity with this verifier and corpus, it does not,
while the other two clauses held. Any follow-up design is a new
pre-registration.

### D31. v2 harness: symbol on the flag, one clause in the oracle, v1 untouched
Function-level localization is implemented by giving flags and symbolised
gold hunks a `symbol` (qualname or `<module>`) and a line span, and by
adding a single clause to `Location.overlaps`: two locations that both name
a symbol must name the same one. This keeps the oracle a deterministic
overlap rule (D27's argument still holds) while closing the loophole where
a `<module>` flag with a whole-file span would score as a file hit. Nothing
at file granularity changes: a file-level flag has no symbol, so v1 runs
replay byte-identically and the v2 file-level secondary is the v1 metric
computed on the stage-1 flags. The stage-1 prompt is the v1 prompt on
purpose: same cache keys, so no v1 spend is repeated. Consolidation keys on
`path # qualname` inside the record's location string, so the file-keyed
seam (D24) becomes function-keyed with no new gate logic. Evaluation is
N-arm with one shared task set (a failure in any arm drops the task from
all), and per-task hits are written to `arms.json` so the paired analysis
needs no corpus. The only genuinely new parsing is the `ast` function
index; its independent witness for Gate 2.3-v2 is an indentation-based
symboliser that shares no code with it.

### D32. v2 as drafted is not feasible; recorded, not registered
The v2 draft fixed a feasibility rule before any pre-run (ceiling ≥ 1.5 ×
MDE) precisely so that this decision would not be a judgement call. The
pre-runs give ceiling 13.0 pts and MDE 10.2 pts at the registered pool of
373 tasks (draft §11, findings §16), so the rule fails and the registered
run is not made. The two paths that could make it feasible — more paired
tasks (n ≥ 521 at this ceiling) or a larger corpus — both require a fresh
§5.1/§5.2 before any value is filled; neither is chosen here, and neither
the 1.5× margin nor the ceiling definition is revisited after seeing the
numbers. Treatment spend: none.

### D33. Sizing v2: recommend prequential evaluation, not more repos (owner to decide)
Run 26 (findings §17) shows the registered one-split rule, not the corpus,
capped the pool: repos with short chains add nothing under it. A
prequential design on the same 10 repos is feasible under the draft's
unchanged rules (ceiling 15.6, MDE 8.6, pool 530). Two further levers are
recorded with their assumptions — paired power (needs an assumed
discordance share) and class granularity (needs its own control run and
is a different hypothesis) — and neither is relied on. No design is
chosen here; the recommendation is design A in draft §12, and picking it
means a rolling-evaluation mode in the harness before §5.2/§5.3 are re-run
and the block is filled and tagged.

### D34. Design A adopted: rolling evaluation built; τ calibrated on the excluded repos
Owner chose design A (2026-09-11). The rolling mode fixes the per-task
order (all arms localize, then the control flags are ingested, then tick)
so the memory an arm sees is exactly the snapshot after the previous task
and the learning stream never depends on memory's effect or on arm order.
Because design A scores every post-warm-up task, τ cannot be calibrated
on "build tasks" without leakage; it is calibrated instead on the two
repos v1's ceiling rule excluded from treatment (streamlink, pvlib), which
are never scored as treatment. Values for the block are in draft §13; τ is
the last fill. The paired MDE is reported with an assumed discordance of
0.30, chosen before any treatment data and above v1's 0.09; the kill
number does not depend on it.

### D35. v2 registered: primary arm ungated, gated as secondary, placebo arm added
Owner chose option 2 with the placebo arm (draft §14) on 2026-09-11.
Registered in `docs/PREREGISTRATION-v2.md` with `docs/exp-run.v2.json`
(branch `prereg/v2`). The primary comparison is the ungated memory arm
against control, as in v1, so v2 differs from v1 by granularity alone;
gating at τ = 0.50 is measured as a secondary. The placebo arm injects,
on every task, as many memory lines as the treatment arm does, drawn by
the same retrieval similarity from a fixed pool of five promoted memories
from two repositories outside the experiment (streamlink, pvlib; run 8;
`docs/placebo-pool.v2.json`, sha256 pinned in the block). H2 requires
treatment − placebo ≥ 4.5 pts in addition to the kill number, the FP
ceiling and the inert negative control: a lift the placebo matches is
prompt perturbation, not memory (run 8 showed exactly that). The run is
sharded by repository (A/B/C) to fit the runner's job limit; sharding is
exact and the merge refuses duplicates.

### D36. Registered run interrupted by the API key's spend cap; resumed, not restarted
Shards A/B/C (runs 10–12) started 2026-09-11 15:52 and hit OpenRouter
HTTP 402 ("in-flight budget exhausted", retryable) and then HTTP 403 ("Key
limit exceeded (total limit)") within ~40 minutes; shard A wrote no
results, B and C wrote partial ones (`results/experiment/{11,12}/`,
kept for the record, **not results**). Nothing about the design changed.
Recovery: the shards are re-run with `resume_run` pointing at their own
artifacts, so every call that succeeded is served from the
content-addressed cache and only the failed calls are made; the rolling
chain is replayed from task 1, so memory state is exactly what an
uninterrupted run would have produced. Mechanics changes made before the
relaunch, none touching a registered value: 402 is now retried with
backoff; the salvage regex accepts a stray quote closing the last string
(one cfn-lint response); a circuit breaker stops a shard after 10
consecutive task failures instead of burning through the chain; and
`phase2.check_config` verifies every shard's config against
`docs/exp-run.v2.json` at merge time, ignoring only the run-mechanics keys
(`repos` must be a registered shard, `shard`, `resume_run`,
`secondary_repos`). The registered block's wording ("except the repos
list") predates the `shard`/`resume_run` keys; this decision, not the
block, is the record of that clarification.

### D37. One duplicated corpus row (conan-18153) dropped at load; registered pool 530 → 529
The resumed shard A (run 13) crashed deterministically at the second
occurrence of `conan-io__conan-18153`, which the published SWE-bench-Live
`full` split carries twice: identical record ids hit the buffer's
"already supports" invariant. `read_tasks` now keeps the first occurrence
of an instance id and reports the drop. Effect on registered values:
conan's chain is 164 not 165, the eval pool 529 not 530; MDE (8.6), ceiling
(15.6), kill number (9) and every other value are unchanged at this
precision, and v1's registered pool of 373 is unaffected (the duplicate sat
past v1's split). No design value was touched; the fix is corpus hygiene
and applies identically to every arm. Run 13 made no model calls (every
call was a cache hit), so the key's status is still untested.

### D38. v2 verdict: killed as registered; no further registered runs on this thesis
The registered v2 run (findings §20) fails the kill number (−1.33 pts vs
≥ 9), fails the placebo margin (−0.57 vs ≥ 4.5), and fails the majority
criterion; it passes the FP ceiling and the negative control. Both
registered experiments on the thesis "memory of prior defects improves
localization" are now negative at the two granularities the data
supported, with clean mechanics each time (traceable beliefs, inert
negative control, flat false positives). The placebo arm adds the
diagnostic v1 lacked: the verifier's response to memory is mostly a
response to the prompt's shape. No third registration is proposed on
this corpus with this verifier; a different thesis (e.g. memory as a
*veto* on repeated false positives rather than a pointer to gold, or
memory consumed by a retrieval-augmented localizer that reads code
rather than a file listing) would be a new experiment, not a v3.
