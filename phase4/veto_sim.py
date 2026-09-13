"""Exploratory (post hoc, NOT registered): what a *veto* memory would have done.

A veto memory remembers locations the verifier flagged wrongly and suppresses
them later. Simulated prequentially on the control arm's recorded flags from
the rolling runs: a location becomes vetoed after it has been a false positive
k times and a true positive never; from then on its flags are dropped. Learning
happens after scoring each task, so no task sees its own outcome. The
simulation is a *filter* (flags removed, nothing re-asked), so it cannot raise
hit@3; it can only trade correct flags for false positives.

    python -m phase4.veto_sim --dirs results/experiment/18/rolling,results/experiment/19/rolling,results/experiment/20/rolling \
        --negative-control sissbruecker/linkding [--k 2] [--level file|function]
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def simulate(files, level: str, k: int, negative_control: str | None):
    tot = collections.Counter(); per = {}
    for f in files:
        a = json.loads(Path(f).read_text()); repo = Path(f).name[: -len(".arms.json")].replace("__", "/", 1)
        if repo == negative_control:
            continue
        gold, flags = a["gold"], a["arms"]["control"]["flags"]
        key = (lambda s: s) if level == "function" else (lambda s: s.split("::")[0])
        wrong, right = collections.Counter(), collections.Counter()
        c = collections.Counter()
        for iid, fl in flags.items():                      # chronological in rolling mode
            if iid not in gold:
                continue
            g = {key(x) for x in gold[iid]}
            kept, removed_fp, removed_ok = [], 0, 0
            for s in fl:
                loc = key(s); ok = loc in g
                if wrong[loc] >= k and right[loc] == 0:
                    removed_fp += (not ok); removed_ok += ok
                else:
                    kept.append(ok)
                (right if ok else wrong)[loc] += 1
            c["tasks"] += 1; c["flags"] += len(fl); c["fp"] += sum(1 for s in fl if key(s) not in g)
            c["hit_before"] += any(key(s) in g for s in fl); c["hit_after"] += any(kept)
            c["removed_fp"] += removed_fp; c["removed_ok"] += removed_ok; c["tasks_touched"] += (removed_fp + removed_ok > 0)
        per[repo] = dict(c); tot.update(c)
    return dict(tot), per


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dirs", required=True); ap.add_argument("--negative-control"); ap.add_argument("--k", type=int, default=2); ap.add_argument("--level", default="file", choices=["file", "function"])
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args(argv)
    files = [f for d in a.dirs.split(",") if d for f in sorted(Path(d).glob("*.arms.json"))]
    tot, per = simulate(files, a.level, a.k, a.negative_control)
    n, fl, fp = tot["tasks"], tot["flags"], tot["fp"]
    rm_fp, rm_ok = tot.get("removed_fp", 0), tot.get("removed_ok", 0)
    print(f"{a.level} k={a.k}: tasks={n} flags={fl} FP={fp} ({fp/fl:.3f}) | removed FP={rm_fp} ({rm_fp/fp:.1%}) correct={rm_ok} | hit@3 {tot['hit_before']/n:.3f} -> {tot['hit_after']/n:.3f} | FP rate {fp/fl:.3f} -> {(fp-rm_fp)/(fl-rm_fp-rm_ok):.3f} | veto precision {rm_fp/max(rm_fp+rm_ok,1):.2f}")
    for r, c in per.items():
        print(f"  {r:30s} FP removed {c.get('removed_fp',0):3d}/{c['fp']:3d} correct removed {c.get('removed_ok',0):2d} hit {c['hit_before']/c['tasks']:.3f} -> {c['hit_after']/c['tasks']:.3f}")
    if a.json_out:
        Path(a.json_out).write_text(json.dumps({"level": a.level, "k": a.k, "total": tot, "per_repo": per}, indent=1))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
