# EXP-001 v2.0 — Consolidated Memory for Defect Localization

Does a verifier that accumulates codebase-specific memory of prior defects
localize more subsequent defects — without inflating false positives — and is
every belief it acquired traceable to the evidence that produced it?

Full spec: [docs/EXP-001.md](docs/EXP-001.md). Gate tracker:
[docs/GATES.md](docs/GATES.md). Decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

**Status:** Phase 1 kernel passes its mechanism assertions on synthetic
streams. Phase 0–4 harness built and tested offline end to end. Phase 0
corpus runs done on GitHub Actions (`results/phase0/`): no Claude model
still served passes the freshness gate on the Python corpus, so the
verifier will be an open-weights model with a documented cutoff (option A,
recommended Llama 3.3 70B; [docs/phase0-findings.md](docs/phase0-findings.md) §6).
Control arm measured on the pinned verifier across the 13 draft repos:
hit@3 0.673, determinism identical (`results/phase0/18/`, findings §8).
Nothing pre-registered yet.
Similarity seam is still the Jaccard placeholder (D14).

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
  persist.py          save/load a kernel between phases (ledger re-verified on load)
  provenance.py       knew_by_causal_order vs knew_by_wall_clock
  synthetic.py        event streams with known properties (Phase 1)
adapters/code/        GitHub / SWE-bench-Live adapter
  oracle.py           flagged location vs gold hunks -> good | bad | unknown
  similarity.py       embedding cosine with content-hash cache (Phase 2 pins the model)
  policy.py           §6 promotion constants
  pipeline.py         one kernel per repo: learn (Phase 3) and two-arm evaluate (Phase 4)
phase2/               power.py (n per arm / MDE), handcheck.py (oracle vs manual labels)
phase3/learn.py       build split -> kernel.json + gate3.json per repo
phase4/evaluate.py    eval split, both arms interleaved -> gate4.json
phase0/               baseline reproduction (RUNBOOK.md)
  freshness_gate.py   tasks must postdate every model cutoff — enforced at import
  corpus.py           SWE-bench-Live pull / local load -> tasks.jsonl
  chains.py           per-repo chronological chains, split eligibility, report
  ground_truth.py     gold patch -> hunk locations (feeds oracle + metric)
  timemachine.py      pip pinning to base_commit date; freeze audit
  verifier.py         control-arm file localizer; cached model client (determinism)
  metrics.py          paired localization / false-positive rates, per repo
  run_control.py      end-to-end control run + rerun comparison
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
