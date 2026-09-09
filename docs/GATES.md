# Gate tracker

Any gate can end the experiment. Tick boxes only with evidence linked.

## Gate 0 — Baseline (Phase 0)
Harness: `phase0/` (see `phase0/RUNBOOK.md`). Built and unit-tested; not yet run on the corpus.

- [ ] Control-arm localization rate within a defensible margin of a published baseline — reference: ______ (metric, k, model, corpus) · our number: ______ (`runs/control-001/metrics.json`)
- [x] Freshness gate enforced in code, not by convention — `phase0/freshness_gate.py`, applied at import in `phase0/corpus.py`; `tests/test_freshness_gate.py`
- [ ] Harness reruns produce identical results on identical inputs — `run_control --compare` exit 0 on an `--offline` rerun (mechanism: content-addressed response cache, `tests/test_verifier.py::test_cache_makes_rerun_identical_and_offline`)
- [ ] Corpus decision (§9.1) recorded from `docs/chain-report.md`

## Gate 1 — Mechanism (Phase 1)
Run: `make gate1`

| Assertion | Test | Status |
|---|---|---|
| Surprise gate discards the injected redundant fraction within tolerance | `tests/test_surprise_gate.py` | passing |
| Promotion fires exactly at threshold, never earlier | `tests/test_promotion_gate.py::test_fires_exactly_at_threshold` | passing |
| TTL removes unpromoted entries | `tests/test_ttl.py` | passing |
| Same input + same memory version → identical output, every time | `tests/test_replay.py` | passing |
| Clock skew: wall clock provably wrong, causal order right | `tests/test_clock_skew.py` | passing |
| Supersession creates a new object; no mutation | `tests/test_supersession.py` | passing |

- [x] All mechanism assertions pass (33 tests, `make test`)
- [x] Clock-skew demonstration reproducible and written up — `docs/clock-skew.md`

**Gate 1 status: passing on the synthetic kernel.** It stays provisional until
the same assertions hold with the real similarity seam (embedding cosine) in
Phase 2 — determinism of the embedding cache is the risk.

## Gate 2 — Corpus (Phase 2)
Tooling: `phase2/power.py` (n per arm / MDE), `phase2/handcheck.py` (oracle vs manual, exit 1 below 95%),
`adapters/code/pipeline.py` (three seams wired to the kernel; `tests/test_pipeline.py`).

- [ ] Pre-registration published and timestamped — `docs/PREREGISTRATION.md`
- [ ] Per-repo chains ≥ power-calc minimum in the build split — `python -m phase2.power --p0 <Gate 0 rate> --mde 0.15` vs `docs/chain-report.md`
- [ ] Oracle agreement with manual labels ≥ 95% on a 50-instance hand-check — `python -m phase2.handcheck score handcheck.csv`
- [ ] Similarity seam replaced with pinned embedding cosine and Θ re-tuned (D14)

## Gate 3 — Learning (Phase 3) — expected failure point
Run: `python -m phase3.learn …` → `runs/learn-*/<repo>/gate3.json`

- [ ] Surprise gate discards > 60% of candidate writes — `gate3.json: discard_rate`
- [ ] ≥ floor promoted memories per repo (floor from pre-registration) — `gate3.json: promoted`
- [ ] Promoted memories human-legible on inspection — read `kernel.json: objects[].content`

## Gate 4 — Result (Phase 4)
Run: `python -m phase4.evaluate …` → `runs/eval-*/gate4.json`

- [ ] Localization lift ≥ 15 pts absolute (or MDE if higher) — `localization_lift_pts`
- [ ] False-positive rise ≤ 5 pts absolute — `false_positive_rise_pts`
- [ ] Effect in a majority of repos — `effect_in_majority_of_repos`
- [ ] Negative-control repo shows no lift — `negative_control_lift`
