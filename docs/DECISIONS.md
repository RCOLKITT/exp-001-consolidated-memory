# Decision log

Open decisions from spec §9 plus design decisions made while building the
kernel. Each entry: what was decided, why, and what it forecloses.

## Open (spec §9)
1. **Primary corpus** — ChainSWE vs SWE-bench-Live. Resolve in Phase 0 by
   measuring per-repo chain length.
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
