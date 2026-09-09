# EXP-001 v2.0 — Consolidated Memory for Defect Localization

Does a verifier that accumulates codebase-specific memory of prior defects
localize more subsequent defects — without inflating false positives — and is
every belief it acquired traceable to the evidence that produced it?

Full spec: [docs/EXP-001.md](docs/EXP-001.md). Gate tracker:
[docs/GATES.md](docs/GATES.md). Decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

**Status:** Phase 1 kernel built and passing its mechanism assertions on
synthetic streams. Phase 0 not started. Nothing pre-registered.

## Layout

```
memkernel/            domain-independent kernel (no dependencies)
  vclock.py           vector clocks — causal ordering tokens
  records.py          Record, MemoryObject (immutable, content-addressed)
  seams.py            the three seams: Oracle, Similarity, (Contradiction)
  buffer.py           episodic buffer with TTL + reinforcement
  gates.py            surprise gate, promotion gate (§6 policy)
  store.py            versioned append-only memory store, supersession
  ledger.py           hash-chained outcome ledger
  kernel.py           orchestration; every mutation traced for replay
  replay.py           replay a trace, compare two kernels
  provenance.py       knew_by_causal_order vs knew_by_wall_clock
  synthetic.py        event streams with known properties (Phase 1)
adapters/code/        GitHub / SWE-bench-Live adapter (Phase 2; stubs + §6 config)
phase0/               baseline reproduction; freshness gate (enforced in code)
tests/                one test file per mechanism assertion
docs/                 spec, pre-registration, gates, decisions, clock-skew write-up
```

## Run

```
make install     # pip install -e ".[dev]"
make test        # all tests
make gate1       # only the six Gate 1 mechanism assertions
```

## How the kernel flows

```
record ──► oracle.label ──► retrieve(pinned version) ──► surprise gate
                                                          │
                              surprise > Θ ───────────────┼──► buffer (new entry)
                              redundant to buffer entry ──┼──► reinforce that entry
                              redundant to promoted mem ──┴──► discard (logged)

tick ──► expire TTL ──► every N ticks: promotion gate (§6) ──► store.put(MemoryObject)
freeze ──► store.freeze() = version id; promotion disabled; retrieval pinned
```

Every step appends to the ledger with a vector clock. Replaying the trace
yields the same ledger hashes, same memory ids, same versions
(`tests/test_replay.py`).

## Phase 4 arms, in kernel terms

| Arm | Kernel call |
|---|---|
| Control | `kernel.pin(None)` — retrieval returns nothing |
| Treatment | `kernel.pin(frozen_version)` — retrieval from the frozen snapshot |

## Non-goals (spec §1)
No patch generation, no weight-level learning, no cross-repo memory, no
adaptive thresholds, no rule compilation, no customer or private data.
