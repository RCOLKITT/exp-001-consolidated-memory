"""Design A — prequential (rolling) evaluation (v2 draft §12).

    python -m phase4.rolling --tasks corpus/tasks.jsonl --repos a/b,c/d --warmup 20 --repos-dir corpus/repos \
        --out runs/rolling --seed 11 --arms control,treatment,ungated --granularity function --consolidation function --tau 0.55 \
        [--negative-control owner/name] [--model ...] [seam args]

Per repo: every task after the warm-up is an eval task scored by every arm
against the memory built from all earlier tasks (adapters.code.pipeline
.RepoPipeline.rolling). Writes per repo `arms.json` (per-task flags, hits,
memory version seen), `gate3.json` (learning diagnostics over the whole
chain), `kernel.json` (final frozen kernel + ledger), and `gate4.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.code.pipeline import ArmSpec, write_json
from memkernel.persist import save_kernel
from phase0.chains import build_chains
from phase0.corpus import apply_freshness, read_tasks
from phase3.learn import add_seam_args, make_pipeline
from phase4.report import Aggregator, arms_json


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--repos", required=True, help="comma list of owner/name (treatment repos + negative control)")
    ap.add_argument("--warmup", type=int, default=20); ap.add_argument("--out", required=True)
    ap.add_argument("--models"); ap.add_argument("--repos-dir", default="corpus/repos"); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high"); ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"]); ap.add_argument("--base-url"); ap.add_argument("--api-key-env", default="MODEL_API_KEY"); ap.add_argument("--model-extra", default="")
    add_seam_args(ap)
    ap.add_argument("--ttl", type=int, default=30); ap.add_argument("--negative-control"); ap.add_argument("--cache"); ap.add_argument("--offline", action="store_true")
    ap.add_argument("--arms", default="control,treatment", help="control (no memory), treatment (memory, gate τ = --tau), ungated (memory, τ = 0)")
    ap.add_argument("--max-tasks-per-repo", type=int, default=0, help="cap chain length per repo (smoke runs only)")
    args = ap.parse_args(argv)
    arm_names = [a.strip() for a in args.arms.split(",") if a.strip()]
    if "control" not in arm_names or "treatment" not in arm_names:
        ap.error("--arms must include control and treatment")
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tasks = read_tasks(args.tasks)
    if args.models:
        tasks = apply_freshness(tasks, args.models, out / "freshness.jsonl")
    agg = Aggregator(arm_names, args.granularity, args.tau)
    for chain in build_chains(tasks):
        if chain.repo not in repos:
            continue
        chain_tasks = list(chain.tasks)[: args.max_tasks_per_repo] if args.max_tasks_per_repo else list(chain.tasks)
        rd = out / chain.repo.replace("/", "__")
        p = make_pipeline(chain.repo, chain_tasks, args, Path(args.cache) if args.cache else rd / "cache.jsonl")
        tau = {"control": 0.0, "treatment": args.tau, "ungated": 0.0}
        specs = [ArmSpec(n, None if n == "control" else "rolling", tau.get(n, args.tau)) for n in arm_names]
        is_neg = chain.repo == args.negative_control
        arms = p.rolling(chain_tasks, args.warmup, args.seed, specs, learn=not is_neg)
        save_kernel(p.kernel, rd / "kernel.json")
        ev = chain_tasks[args.warmup:]
        repo_of = {t.instance_id: chain.repo for t in ev}
        stats = p.gate3_stats(); stats.update({"n_tasks": len(chain_tasks), "n_eval": len(ev), "warmup": args.warmup, "granularity": args.granularity, "tau": args.tau,
                                               "consolidation": getattr(p.kernel.similarity, "name", args.consolidation), "retrieval": getattr(p.kernel.retrieval_similarity, "name", ""),
                                               "min_occurrences": args.min_occurrences, "min_distinct_inputs": args.min_distinct_inputs, "negative_control": is_neg})
        write_json(stats, rd / "gate3.json")
        aj = arms_json(arms, p.truth, repo_of, args.granularity, {"mode": "rolling", "warmup": args.warmup, "n_eval": len(ev), "learn_errors": stats["learn_errors"],
                                                                   "memory_locations": p.memory_locations(), "gold": p.gold_keys(ev)})
        write_json(aj, rd / "arms.json")
        agg.add(chain.repo, arms, p.truth, repo_of, aj, is_neg)
        mc, mt = aj["control"], aj["treatment"]
        sys.stderr.write(f"{chain.repo}: chain={len(chain_tasks)} eval={len(ev)} errors={aj['n_errors']} promoted={stats['promoted']} discard={stats['discard_rate']} | control loc={mc['localization_rate']:.3f} fp={mc['false_positive_rate']:.3f} | treatment loc={mt['localization_rate']:.3f} fp={mt['false_positive_rate']:.3f} | lift={aj['lift']}\n")
    report = agg.report({"mode": "rolling", "warmup": args.warmup})
    write_json(report, out / "gate4.json")
    sys.stdout.write(json.dumps({k: report[k] for k in report if k not in ("control", "treatment")}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
