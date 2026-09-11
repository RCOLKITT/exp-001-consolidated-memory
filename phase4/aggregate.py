"""Merge sharded rolling runs: rebuild gate4.json from per-repo arms.json files.

    python -m phase4.aggregate --dirs results/experiment/10/rolling,results/experiment/11/rolling \
        --negative-control sissbruecker/linkding --out results/experiment/13/rolling

Sharding by repository is exact — each repository has its own kernel and
its own chain — so the aggregate over shards equals a single run's gate4.
Copies every arms.json / gate3.json into --out so `phase4.paired` runs on it.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from phase4.report import Aggregator, metrics_from_json


def aggregate(dirs: list[Path], negative_control: str | None, out: Path) -> dict:
    files = [f for d in dirs for f in sorted(d.glob("*.arms.json"))]
    if not files:
        raise SystemExit("no arms.json files found")
    first = json.loads(files[0].read_text())
    arm_names = list(first["arms"])
    agg = Aggregator(arm_names, first.get("granularity", "file"), first["arms"]["treatment"].get("tau", 0.0))
    out.mkdir(parents=True, exist_ok=True)
    seen = set()
    for f in files:
        repo = f.name[: -len(".arms.json")].replace("__", "/", 1)
        if repo in seen:
            raise SystemExit(f"repository {repo} appears in more than one shard")
        seen.add(repo)
        a = json.loads(f.read_text())
        agg.add_metrics(repo, {n: metrics_from_json(v["metrics"]) for n, v in a["arms"].items()},
                        {n: metrics_from_json(v["file_metrics"]) for n, v in a["arms"].items()}, a, repo == negative_control)
        shutil.copy(f, out / f.name)
        g3 = f.with_name(f.name.replace(".arms.json", ".gate3.json"))
        if g3.exists():
            shutil.copy(g3, out / g3.name)
    rep = agg.report({"mode": first.get("mode", "rolling"), "warmup": first.get("warmup"), "shards": [str(d) for d in dirs], "repos": sorted(seen)})
    (out / "gate4.json").write_text(json.dumps(rep, indent=1, sort_keys=True))
    return rep


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dirs", required=True); ap.add_argument("--negative-control"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rep = aggregate([Path(d) for d in a.dirs.split(",") if d], a.negative_control, Path(a.out))
    sys.stdout.write(json.dumps({k: rep[k] for k in rep if k not in ("control", "treatment", "secondary_arms")}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
