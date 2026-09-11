"""Phase 4 — evaluation: both arms on the eval split, interleaved, seeded.

    python -m phase4.evaluate --tasks corpus/tasks.jsonl --split corpus/split.json \
        --learn-dir runs/learn-001 --repos-dir corpus/repos --out runs/eval-001 --seed 7 \
        [--negative-control owner/name] [--model claude-opus-5]

Writes per-repo control/treatment flags + metrics and `gate4.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.code.pipeline import ArmSpec, parse_arms, write_json
from memkernel.persist import load_kernel
from phase0.chains import build_chains
from phase0.corpus import apply_freshness, read_tasks
from phase3.learn import add_seam_args, make_pipeline
from phase4.report import Aggregator, arms_json


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True); ap.add_argument("--split", required=True); ap.add_argument("--learn-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--models"); ap.add_argument("--repos-dir", default="corpus/repos"); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--model", default="claude-opus-5"); ap.add_argument("--effort", default="high"); ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--provider", default="anthropic", choices=["anthropic", "openai-compatible"]); ap.add_argument("--base-url"); ap.add_argument("--api-key-env", default="MODEL_API_KEY"); ap.add_argument("--model-extra", default="")
    add_seam_args(ap)
    ap.add_argument("--ttl", type=int, default=30); ap.add_argument("--negative-control"); ap.add_argument("--cache"); ap.add_argument("--offline", action="store_true")
    ap.add_argument("--max-eval-per-repo", type=int, default=0, help="cap eval tasks per repo (smoke runs only)")
    ap.add_argument("--arms", default="control,treatment", help="name[:tau] list, e.g. control,treatment:0,gated:0.5,placebo:0")
    ap.add_argument("--placebo-pool", help="JSON {\"pool\": [contents...]} of memories from repositories outside the experiment")
    args = ap.parse_args(argv)
    try:
        arm_specs = parse_arms(args.arms, args.tau)
    except ValueError as e:
        ap.error(str(e))
    arm_names = [a.name for a in arm_specs]
    placebo_pool = [m["content"] if isinstance(m, dict) else str(m) for m in json.loads(Path(args.placebo_pool).read_text())["pool"]] if args.placebo_pool else []
    if any(a.kind == "placebo" for a in arm_specs) and not placebo_pool:
        ap.error("a placebo arm needs --placebo-pool")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    tasks = read_tasks(args.tasks)
    if args.models:
        tasks = apply_freshness(tasks, args.models, out / "freshness.jsonl")
    split = json.loads(Path(args.split).read_text())
    agg = Aggregator(arm_names, args.granularity, args.tau)
    for chain in build_chains(tasks):
        if chain.repo not in split:
            continue
        _, ev = chain.split(int(split[chain.repo]))
        if args.max_eval_per_repo:
            ev = ev[: args.max_eval_per_repo]          # smoke runs only; never for the pre-registered evaluation
        rd = out / chain.repo.replace("/", "__")
        p = make_pipeline(chain.repo, chain.tasks, args, Path(args.cache) if args.cache else rd / "cache.jsonl")
        p.placebo_pool = tuple(placebo_pool)
        kpath = Path(args.learn_dir) / chain.repo.replace("/", "__") / "kernel.json"
        if chain.repo == args.negative_control or not kpath.exists():
            p.frozen_version = p.kernel.freeze()             # empty memory, still two arms
        else:
            load_kernel(kpath, p.kernel)
            p.frozen_version = p.kernel.pinned_version
        specs = [ArmSpec(a.name, None if a.kind == "control" else p.frozen_version, a.tau, a.kind) for a in arm_specs]
        arms = p.evaluate_arms(ev, args.seed, specs)
        repo_of = {t.instance_id: chain.repo for t in ev}
        aj = arms_json(arms, p.truth, repo_of, args.granularity)
        write_json(aj, rd / "arms.json")
        agg.add(chain.repo, arms, p.truth, repo_of, aj, chain.repo == args.negative_control)
        mc, mt = aj["control"], aj["treatment"]
        sys.stderr.write(f"{chain.repo}: n={len(ev)} errors={aj['n_errors']} control loc={mc['localization_rate']:.3f} fp={mc['false_positive_rate']:.3f} | treatment loc={mt['localization_rate']:.3f} fp={mt['false_positive_rate']:.3f} | lift={aj['lift']}\n")
    report = agg.report()
    write_json(report, out / "gate4.json")
    sys.stdout.write(json.dumps({k: report[k] for k in report if k not in ("control", "treatment")}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
