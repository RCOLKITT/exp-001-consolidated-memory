"""Write corpus/split.json (repo -> N build tasks) from the gated corpus.

    python -m phase2.make_split corpus/tasks.jsonl --repos a/b,c/d --build 20 --min-eval 10 \
        [--ceiling-metrics results/phase0/18/control/metrics.json --ceiling 0.90] --out corpus/split.json

The ceiling rule (D19) drops repos whose Phase 0 control hit@k is >= --ceiling;
it is applied only if --ceiling-metrics is given, and the dropped repos are
printed so the pre-registration can list them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phase0.chains import build_chains
from phase0.corpus import read_tasks


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks"); ap.add_argument("--repos", required=True); ap.add_argument("--build", type=int, default=20)
    ap.add_argument("--min-eval", type=int, default=10); ap.add_argument("--ceiling-metrics"); ap.add_argument("--ceiling", type=float, default=0.90)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    wanted = [r.strip() for r in a.repos.split(",") if r.strip()]
    chains = {c.repo: c for c in build_chains(read_tasks(a.tasks))}
    dropped = {}
    if a.ceiling_metrics:
        per = json.loads(Path(a.ceiling_metrics).read_text())["per_repo"]
        for r in wanted:
            rate = per.get(r, {}).get("localization_rate")
            if rate is not None and rate >= a.ceiling:
                dropped[r] = rate
    split = {}
    for r in wanted:
        if r in dropped or r not in chains:
            continue
        if len(chains[r]) < a.build + a.min_eval:
            sys.stderr.write(f"skip {r}: {len(chains[r])} tasks < {a.build}+{a.min_eval}\n"); continue
        split[r] = a.build
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(split, indent=1, sort_keys=True))
    sys.stderr.write(f"split: {len(split)} repos, build={a.build}; dropped at ceiling {a.ceiling}: {dropped}\n")
    sys.stdout.write(json.dumps({"split": split, "dropped_ceiling": dropped}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
