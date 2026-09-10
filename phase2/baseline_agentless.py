"""Gate 0.1 reference: Agentless file-level localization, recomputed with our
metric from the authors' published `loc_outputs.jsonl` (found_files) and
SWE-bench Lite gold patches.

    python -m phase2.baseline_agentless loc_outputs.jsonl swebench_lite.jsonl --k 3 --out baseline.json

hit@k = share of instances whose top-k found_files contain a gold
(non-test) file — the same definition as phase0.metrics on our corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from phase0.ground_truth import gold_files


def compute(loc_rows, gold_by_id, k):
    n = hit = 0; missing = 0; total_flags = 0; fp = 0
    for r in loc_rows:
        iid = r["instance_id"]
        if iid not in gold_by_id:
            missing += 1; continue
        gold = set(gold_by_id[iid])
        top = [f for f in (r.get("found_files") or [])][:k]
        n += 1
        if any(f in gold for f in top):
            hit += 1
        total_flags += len(top); fp += sum(1 for f in top if f not in gold)
    return {"k": k, "n": n, "hit": hit, "hit_at_k": round(hit / n, 4) if n else None,
            "flags": total_flags, "false_positive_rate": round(fp / total_flags, 4) if total_flags else None, "missing_gold": missing}


def _main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("loc_outputs"); ap.add_argument("tasks_jsonl", help="SWE-bench Lite rows with instance_id and patch"); ap.add_argument("--k", type=int, default=3); ap.add_argument("--out")
    a = ap.parse_args(argv)
    loc = [json.loads(l) for l in Path(a.loc_outputs).read_text().splitlines() if l.strip()]
    tasks = [json.loads(l) for l in Path(a.tasks_jsonl).read_text().splitlines() if l.strip()]
    gold = {t["instance_id"]: gold_files(t["patch"]) for t in tasks}
    res = {str(k): compute(loc, gold, k) for k in (1, 3, 5)}
    res["source"] = {"loc_outputs": a.loc_outputs, "tasks": a.tasks_jsonl, "n_loc_rows": len(loc), "n_tasks": len(tasks)}
    s = json.dumps(res, indent=1)
    if a.out: Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(s)
    print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
