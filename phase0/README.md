# Phase 0 — Baseline reproduction (4 days)

Runs in parallel with Phase 1. Depends on nothing.

## Checklist
- [ ] Stand up SWE-bench-Live locally with per-task Docker images
- [ ] Freshness gate enforced **in code** at import (`freshness_gate.py`) — every task must postdate the training cutoff of every model evaluated; per-task dates recorded for release
- [ ] Time-machine dependency pinning: no package versions later than the base commit timestamp
- [ ] Run the control-arm verifier (no memory) and reproduce a published localization rate
- [ ] Evaluate ChainSWE: per-repo chain lengths (decides §9.1)

## Gate 0
- [ ] Control-arm localization within a defensible margin of a published baseline
- [ ] Freshness gate enforced in code, not by convention
- [ ] Harness reruns produce identical results on identical inputs

**Kill:** cannot reproduce a published baseline → stop.

## Corpus layout (not committed)
```
corpus/
  tasks.jsonl          # one task per line: instance_id, repo, created_at, base_commit, ...
  models.json          # {"model_id": "YYYY-MM-DD training cutoff"}
  images/              # per-task docker images (never commit)
```
`python -m phase0.freshness_gate corpus/tasks.jsonl corpus/models.json` prints
the accepted task list and refuses to emit any task on or before any cutoff.
