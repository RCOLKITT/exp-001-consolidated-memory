# Phase 0 runbook

Two ways to run Phase 0. Both use the same scripts.

## A. On GitHub Actions (no laptop needed)
`.github/workflows/phase0.yml` runs on a hosted runner that can reach Hugging
Face and hold the model key. Start a run either from the Actions tab
("phase0" → Run workflow) or by pushing a branch named `run/phase0-<n>` that
carries a `.phase0-run.json`:
```json
{"dataset": "SWE-bench-Live/SWE-bench-Live", "split": "full", "cutoff": "YYYY-MM-DD",
 "model": "claude-opus-5", "run_control": true, "limit": 50, "top_k": 3}
```
- Small results are committed back to that branch under `results/phase0/<run_number>/`
  (corpus summary with per-month histogram and cutoff survivor counts, chain
  report, and for the control arm: metrics, manifest, flags, compare). Merge
  the branch into main to keep them.
- The corpus and model-response cache are uploaded as 90-day artifacts.
- Secrets (Settings → Secrets and variables → Actions): `ANTHROPIC_API_KEY`
  for `"provider": "anthropic"`, or `MODEL_API_KEY` plus a `"base_url"` for
  `"provider": "openai-compatible"` (Together: `https://api.together.xyz/v1`,
  Fireworks: `https://api.fireworks.ai/inference/v1`, Groq:
  `https://api.groq.com/openai/v1`; the `model` value is the host's id for
  the model, e.g. Together's `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`).
  Without the secret the job exits 2 before spending anything. Keep `limit`
  small first.
- `cutoff` blank = no freshness gate (exploration only). Never report a
  number from an ungated run.
- **OpenRouter (chosen host):** secret `MODEL_API_KEY` = the OpenRouter key;
  `"base_url": "https://openrouter.ai/api/v1"`; `"model": "meta-llama/llama-3.3-70b-instruct"`.
  The control job first writes `results/phase0/<n>/control/endpoints.json`
  (every provider serving the model, with quantisation and price). Pin one
  provider and quantisation for the pre-registration via `model_extra`, e.g.
  `{"provider": {"order": ["<provider_name>"], "allow_fallbacks": false, "quantizations": ["bf16"]}}`.
  Unpinned OpenRouter routing can change the verifier between runs.

## B. On your machine
Everything below is the same pipeline, run locally.

## 0. Setup
```bash
cd ~/ryancolkitt/dev/exp-001-consolidated-memory
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,corpus]"        # datasets, anthropic, pypi-timemachine
export ANTHROPIC_API_KEY=...          # or `ant auth login`
```

## 1. Pull the corpus and apply the freshness gate
Write `corpus/models.json` first — the training cutoff of every model you
will evaluate, as stated by the vendor. This is a pre-registration value.
```json
{"claude-opus-5": "YYYY-MM-DD"}
```
```bash
python -m phase0.corpus pull --split full --out corpus/tasks.jsonl --models corpus/models.json
#  -> corpus/tasks.jsonl (admitted tasks only) + corpus/tasks.freshness.jsonl (per-task verdicts, release this)
```
Only tasks strictly newer than the latest cutoff survive. Undated tasks are rejected.

## 2. Chain report (decides ChainSWE vs SWE-bench-Live, §9.1)
```bash
python -m phase0.chains corpus/tasks.jsonl --min-build 20 --min-eval 10 --md docs/chain-report.md --json corpus/chains.json
```
Commit `docs/chain-report.md`. ChainSWE is 304 issues over 54 repos (mean 5.6
per chain), so unless SWE-bench-Live's full split gives several repos with
30+ fresh tasks, neither corpus supports the split and Gate 2 will say so.

## 3. Control-arm run (no memory)
```bash
python -m phase0.run_control --tasks corpus/tasks.jsonl --models corpus/models.json \
  --repos-dir corpus/repos --out runs/control-001 --top-k 3 --limit 50 \
  --provider openai-compatible --base-url https://api.together.xyz/v1 --api-key-env MODEL_API_KEY \
  --model meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8
```
- Clones each repo once into `corpus/repos/`, checks out `base_commit`, sends
  the issue + file list to the model, records top-k files per task.
- Outputs: `flags.jsonl`, `metrics.json` (localization rate + FP rate, per repo),
  `cache.jsonl` (every model response, content-addressed), `manifest.json`.
- Start with `--limit 50` to check cost and behaviour, then drop the limit.

## 4. Determinism check (Gate 0, item 3)
```bash
python -m phase0.run_control --tasks corpus/tasks.jsonl --models corpus/models.json \
  --repos-dir corpus/repos --out runs/control-002 --cache runs/control-001/cache.jsonl --offline --limit 50
python -m phase0.run_control --compare runs/control-001 runs/control-002   # exit 0 == identical flags
```
`--offline` fails on any cache miss, so a clean rerun proves the harness never
touched the model. Sampling is not deterministic; the cache is the mechanism.

## 5. Published baseline (Gate 0, item 1)
Fill `docs/GATES.md` → Gate 0 with the number you compare against and its
source. Candidate references (file-level localization on SWE-bench-family
corpora): the Agentless paper (arXiv 2407.01489, localization tables) and the
survey numbers in `docs/DECISIONS.md` D10. Record the model, corpus, and k
used by the reference; a defensible margin means same metric definition,
same k, stated model.

## 6. Docker images (deferred, see D8)
Only needed for execution-based checks. When you need them:
```bash
docker pull starryzhang/sweb.eval.x86_64.<instance_id with __ -> _1776_, lowercased>
```
`Task.docker_image` computes the name. For dependency installs inside an
image, run `pypi-timemachine <cutoff>` (cutoff from `phase0.timemachine.cutoff_for`)
and point pip at it; audit with `check_freeze`.

## Gate 0 checklist
- [ ] control-arm localization within a defensible margin of the published reference (step 5)
- [x] freshness gate enforced in code (step 1; `tests/test_freshness_gate.py`)
- [ ] `--compare` exit 0 on a rerun (step 4)

---

# Phases 2–4 (only after Gates 0 and 1)

## 7. Pre-register, then split
Fill `docs/PREREGISTRATION.md`, commit, tag `prereg-v1`. Write `corpus/split.json`
= `{"owner/name": N}` with N build tasks per repo from the chain report and
`python -m phase2.power --p0 <Gate 0 rate> --mde 0.15`. Name the negative-control repo.

## 8. Oracle hand-check (Gate 2.3)
```bash
python -m phase2.handcheck export runs/control-001/flags.jsonl corpus/tasks.jsonl --n 50 --seed 1 --out handcheck.csv
# fill `manual` by reading each gold patch; then:
python -m phase2.handcheck score handcheck.csv
```

## 9. Learn (Phase 3), then freeze
```bash
python -m phase3.learn --tasks corpus/tasks.jsonl --models corpus/models.json --split corpus/split.json \
  --repos-dir corpus/repos --out runs/learn-001 --negative-control owner/name
cat runs/learn-001/*/gate3.json          # discard_rate > 0.60 and promoted >= floor, per repo
```

## 10. Evaluate (Phase 4)
```bash
python -m phase4.evaluate --tasks corpus/tasks.jsonl --models corpus/models.json --split corpus/split.json \
  --learn-dir runs/learn-001 --repos-dir corpus/repos --out runs/eval-001 --seed 7 --negative-control owner/name
cat runs/eval-001/gate4.json
```
Both arms run on every eval task, interleaved, task order seeded. The only
difference between arms is the memory section of the prompt.
