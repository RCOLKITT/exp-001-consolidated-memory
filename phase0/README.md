# Phase 0 — Baseline reproduction (4 days)

Runs in parallel with Phase 1. Depends on nothing. **How to run: [RUNBOOK.md](RUNBOOK.md).**

| Spec item | Module | Status |
|---|---|---|
| 1. Stand up SWE-bench-Live locally | `corpus.py` (HF pull / local load, `Task.docker_image`) | built; Docker images deferred (D8) |
| 2. Freshness gate, enforced at import | `freshness_gate.py`, applied in `corpus.py` and `run_control.py` | built + tested |
| 3. Time-machine dependency pinning | `timemachine.py` | built + tested; exercised only when images are built |
| 4. Control-arm verifier, reproduce a published rate | `verifier.py`, `metrics.py`, `run_control.py` | built + tested offline; **not yet run on the corpus** |
| 5. Evaluate ChainSWE chain lengths | `chains.py` | built + tested; ChainSWE data not obtainable from this session |

Also here: `ground_truth.py` (gold patch -> hunk locations; feeds the oracle and the metric).

## Gate 0
- [ ] Control-arm localization within a defensible margin of a published baseline
- [x] Freshness gate enforced in code, not by convention
- [ ] Harness reruns produce identical results on identical inputs (`run_control --compare`)

**Kill:** cannot reproduce a published baseline → stop.

## Corpus layout (never committed — see .gitignore)
```
corpus/
  models.json              {"model_id": "YYYY-MM-DD training cutoff"}   <- pre-registration value
  tasks.jsonl              admitted tasks
  tasks.freshness.jsonl    per-task verdicts, released with the paper
  repos/<owner>__<name>/   one clone per repo, checked out per task
runs/<name>/               flags.jsonl, metrics.json, cache.jsonl, manifest.json
```
