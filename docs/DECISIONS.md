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
