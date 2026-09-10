# Gate tracker

Any gate can end the experiment. Tick boxes only with evidence linked.

## Gate 0 — Baseline (Phase 0)
Harness: `phase0/` (see `phase0/RUNBOOK.md`). Built and unit-tested; not yet run on the corpus.

- [x] Control-arm localization rate within a defensible margin of a published baseline — reference: Agentless v1.5 GPT-4o file-level hit@3 **0.787** (FP@3 0.728) on SWE-bench Lite, recomputed from the authors' released outputs (`results/baseline/1/baseline-10.json`, findings §13) · ours: **0.673** (FP@3 0.727) with Llama 3.3 70B on gated SWE-bench-Live repos
- [x] Freshness gate enforced in code, not by convention — `phase0/freshness_gate.py`, applied at import in `phase0/corpus.py`; `tests/test_freshness_gate.py`
- [x] Harness reruns produce identical results on identical inputs — run 17: `--offline` rerun identical (`results/phase0/17/control/compare.txt`); mechanism: content-addressed response cache
- [x] Corpus decision (§9.1) — SWE-bench-Live Python `full`, verifier chosen to fit the gate (option A, D16): Llama 3.3 70B → 13 eligible repos (`results/phase0/7`); fallback Llama 4 → 4 (`results/phase0/10`). See `docs/phase0-findings.md` §6

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

- [x] Pre-registration published and timestamped — `docs/PREREGISTRATION.md`, commit `a58d7e20ca6b`, branch `prereg/v1` (2026-09-10)
- [x] Per-repo chains ≥ power-calc minimum — eval pool 373, MDE 9.2 pts < kill number 10 < ceiling 17.9 (PREREGISTRATION.md)
- [x] Oracle agreement ≥ 95% on a 50-instance hand-check — 50/50 with an independent parser plus a row audit (D27, `results/phase0/22/control/`)
- [x] Similarity seam: retrieval by pinned MiniLM cosine, consolidation by file (D20, D23, D24); Θ/ρ/cluster from `results/phase2/4–5` for the semantic variant; end-to-end on real data `results/experiment/4/`
- [x] Promotion threshold and build split fixed from the recurrence ceilings — registered (D25)

## Gate 3 — Learning (Phase 3) — expected failure point
Run: `python -m phase3.learn …` → `runs/learn-*/<repo>/gate3.json`

- [ ] Surprise gate discard rate ≥ 0.40 per repo (registered floor for the file-keyed seam) — `gate3.json: discard_rate`
- [ ] ≥ floor promoted memories per repo (floor from pre-registration) — `gate3.json: promoted`
- [ ] Promoted memories human-legible on inspection — read `kernel.json: objects[].content`

## Gate 4 — Result (Phase 4)
Run: `python -m phase4.evaluate …` → `runs/eval-*/gate4.json`

- [ ] Localization lift ≥ 10 pts absolute (registered; ceiling 17.9, MDE 9.2) — `localization_lift_pts`
- [ ] False-positive rise ≤ 5 pts absolute — `false_positive_rise_pts`
- [ ] Effect in a majority of repos — `effect_in_majority_of_repos`
- [ ] Negative-control repo shows no lift — `negative_control_lift`
