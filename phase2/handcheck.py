"""Oracle hand-check (Gate 2 item 3): oracle vs manual labels on 50 flags.

    python -m phase2.handcheck export runs/control-001/flags.jsonl corpus/tasks.jsonl --n 50 --seed 1 --out handcheck.csv
    # fill the `manual` column with good|bad|unknown by reading the patch, then
    python -m phase2.handcheck score handcheck.csv     # prints agreement, exit 1 if < 0.95

The reviewer sees the flagged file and the gold patch, never the verifier's
reasoning, so the check tests the oracle, not the verifier.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from phase0.corpus import read_tasks
from phase0.ground_truth import ground_truth_from_tasks
from phase0.verifier import file_location

from adapters.code.oracle import Flag

THRESHOLD = 0.95


def sample_flags(flags_rows: list[dict], n: int, seed: int) -> list[tuple[str, str]]:
    pairs = [(r["instance_id"], p) for r in flags_rows for p, _ in r["ranked"]]
    rng = random.Random(seed)
    rng.shuffle(pairs)
    return sorted(pairs[:n])


def export(flags_path: str, tasks_path: str, n: int, seed: int, out: str) -> int:
    rows = [json.loads(l) for l in Path(flags_path).read_text().splitlines() if l.strip()]
    tasks = {t.instance_id: t for t in read_tasks(tasks_path)}
    truth = ground_truth_from_tasks(tasks.values())
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "flagged_path", "oracle", "manual", "gold_files"])
        for iid, path in sample_flags(rows, n, seed):
            gt = truth.locations(iid) or ()
            oracle = "unknown" if truth.locations(iid) is None else ("bad" if any(file_location(path).overlaps(h) for h in gt) else "good")
            w.writerow([iid, path, oracle, "", ";".join(sorted({h.path for h in gt}))])
    return 0


def agreement(csv_path: str) -> tuple[float, int, int]:
    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["manual"].strip()]
    if not rows:
        return 0.0, 0, 0
    agree = sum(1 for r in rows if r["manual"].strip() == r["oracle"])
    return agree / len(rows), agree, len(rows)


def _main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("flags"); e.add_argument("tasks"); e.add_argument("--n", type=int, default=50); e.add_argument("--seed", type=int, default=1); e.add_argument("--out", required=True)
    s = sub.add_parser("score"); s.add_argument("csv")
    a = ap.parse_args(argv)
    if a.cmd == "export":
        return export(a.flags, a.tasks, a.n, a.seed, a.out)
    rate, agree, n = agreement(a.csv)
    print(f"agreement {agree}/{n} = {rate:.3f} (threshold {THRESHOLD})")
    return 0 if n and rate >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
