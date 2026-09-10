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
