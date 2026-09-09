# Phase 0 runbook — run this on a machine with Docker, Hugging Face access, and a model key

Everything below is scripted; the cloud session that built it had none of
the three, so nothing here has been run against the real corpus yet.

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
  --repos-dir corpus/repos --out runs/control-001 --model claude-opus-5 --top-k 3 --limit 50
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
