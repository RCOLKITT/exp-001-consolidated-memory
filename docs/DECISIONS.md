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
